import psutil

from pandaharvester.harvestercore import core_utils
from pandaharvester.harvesterconfig import harvester_config
from pandaharvester.harvestercore.db_proxy_pool import DBProxyPool as DBProxy
from pandaharvester.harvestercore.service_metrics_spec import ServiceMetricSpec

# logger
_logger = core_utils.setup_logger('service_monitor')


# class to monitor the service, e.g. memory usage
class ServiceMonitor(AgentBase):
    # constructor
    def __init__(self, single_mode=False, pid_file):
        AgentBase.__init__(self, single_mode)
        self.db_proxy = DBProxy()
        self.pid_file = pid_file
        self.pid = self.get_master_pid()

    def get_master_pid(self):
        """
        Gets the master pid from the lock file
        :return:
        """
        fh = open(self.pid_file, 'r')

        try:
            pid = int(file.readline())
        except:
            pid = None

        fh.close()
        return pid

    def get_memory(self):
        """
        sum memory of whole process tree starting from master pid
        :return: rss in MiB
        """
        try:
            # obtain master process
            master_process = psutil.Process(self.pid)
            rss = master_process.memory_info()[0]
            for child in master_process.children(recursive=True):
                rss += child.process.memory_info()[0]

            # convert bytes to MiB
            rss_mib = rss / float(2 ** 20)
        except:
            rss_mib = None

        return rss_mib

    # main loop
    def run(self):
        while True:
            _logger.debug('Running service monitor')

            service_metrics = {}

            # get memory usage
            rss_mib = self.get_memory()
            _logger.debug('Memory usage: {0} MiB'.format(rss_mib))

            # TODO: find other metrics

            # convert to json format and write to DB
            service_metrics['rss_mib'] = rss_mib
            service_metrics_spec = ServiceMetricSpec(service_metrics)
            self.db_proxy.insert_service_metrics(service_metrics_spec)

            # check if being terminated
            try:
                sleep_time = harvester_config.service_monitor.sleepTime
            except:
                sleep_time = 300

            if self.terminated(sleep_time, randomize=False):
                return


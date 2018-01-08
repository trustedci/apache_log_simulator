class Log():

    @staticmethod
    def _convert_timestamp(timestamp):
        return timestamp.strftime('%d/%b/%Y:%H:%M:%S')

    def __init__(self, source_ip, address, status, size, user_agent, timestamp, user='-', referer='-'):
        self.source_ip = source_ip
        self.address = address
        self.status = status
        self.size = size
        self.user_agent = user_agent
        self.timestamp = timestamp
        self.user = user
        self.referer = referer
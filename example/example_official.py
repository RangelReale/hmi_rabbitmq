import pprint

from kubragen2.configfile import ConfigFile

from hmi_rabbitmq.configfile import RabbitMQConfigFile
from hmi_rabbitmq.official import RabbitMQOfficialRequest

req = RabbitMQOfficialRequest(namespace='myns', releasename='myrabbitmq', values={
    'configuration': RabbitMQConfigFile(),
    'metrics': {
        'enabled': True,
    }
})

chart = req.generate()

pprint.pprint(chart.data)

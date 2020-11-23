import pprint

from hmi_rabbitmq.configfile import RabbitMQConfigFile
from hmi_rabbitmq.official import RabbitMQOfficialRequest

req = RabbitMQOfficialRequest(namespace='myns', releasename='myrabbitmq', values={
    'configuration': RabbitMQConfigFile(),
    'persistence': {
        # 'existingClaim': 'xx',
    },
    'metrics': {
        'enabled': True,
        'serviceMonitor': {
            'enabled': True,
        }
    }
})

chart = req.generate()

pprint.pprint(chart.data)

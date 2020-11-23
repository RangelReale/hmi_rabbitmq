import pprint

from kubragen2.kdata import KData_Env, KData_Secret

from hmi_rabbitmq.configfile import RabbitMQConfigFile
from hmi_rabbitmq.official import RabbitMQOfficialRequest

req = RabbitMQOfficialRequest(namespace='myns', releasename='myrabbitmq', values={
    'configuration': RabbitMQConfigFile(),
    'extraEnvVars': [{
        'name': 'XXX',
        'value': 'YYY',
    }, KData_Env(name='HH', value=KData_Secret('JJ', 'HHHH'))],
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

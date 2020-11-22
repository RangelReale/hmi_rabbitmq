import pprint

from hmi_rabbitmq.official import RabbitMQOfficialRequest

req = RabbitMQOfficialRequest(namespace='myns', releasename='myrabbitmq', values={

})

chart = req.generate()

pprint.pprint(chart.data)

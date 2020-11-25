import unittest

from hmi_rabbitmq import RabbitMQChartRequest


class TestChart(unittest.TestCase):
    def test_empty(self):
        req = RabbitMQChartRequest()
        chart = req.generate()
        self.assertEqual(len(chart.data), 8)

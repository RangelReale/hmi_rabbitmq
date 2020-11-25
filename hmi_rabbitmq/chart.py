from typing import Optional, Mapping, Any, Sequence, List, Dict

from helmion.chart import Chart
from helmion.config import Config
from helmion.data import ChartData
from kubragen2.configfile import ConfigFileRender_SysCtl, ConfigFileRender_RawStr
from kubragen2.data import ValueData, Data
from kubragen2.kdatahelper import KDataHelper_ConfigFile, KDataHelper_Env
from kubragen2.options import Options, OptionValue, OptionsBuildData

from hmi_rabbitmq.configfile import RabbitMQConfigFile
from hmi_rabbitmq.private.chart import PersistenceData, VolumeClaimTemplate


class RabbitMQChartRequest:
    """
    Based on `rabbitmq/diy-kubernetes-examples <https://github.com/rabbitmq/diy-kubernetes-examples>`_.
    """
    config: Config
    namespace: Optional[str]
    releasename: str
    values: Optional[Mapping[str, Any]]
    _options: Options
    _serviceaccount: str

    def __init__(self, namespace: Optional[str] = 'default', releasename: str = 'rabbitmq',
                 values: Optional[Mapping[str, Any]] = None, config: Optional[Config] = None):
        self.namespace = namespace
        self.releasename = releasename
        self.values = values
        self.config = config if config is not None else Config()
        self._options = Options({
            'base': {
                'namespace': namespace,
                'releasename': releasename,
            },
        }, self.allowedValues(), self.values)
        self._serviceaccount = self._options.option_get_opt('serviceAccount.name', self.name_format())

    def options(self) -> Options:
        return self._options

    def allowedValues(self) -> Mapping[str, Any]:
        return {
            'image': {
                'registry': 'docker.io',
                'repository': 'rabbitmq',
                'tag': '3.8.9-alpine',
            },
            'clusterDomain': 'cluster.local',
            'auth': {
                'username': 'user',
                'password': '',
                'existingPasswordSecret': '',
                'erlangCookie': '',
                'existingErlangSecret': '',
                'tls': {
                    'enabled': False,
                    'failIfNoPeerCert': True,
                    'sslOptionsVerify': 'verify_peer',
                    'caCertificate': '',
                    'serverCertificate': '',
                    'serverKey': '',
                    'existingSecret': '',
                }
            },
            'logs': '-',
            'memoryHighWatermark': {
                'enabled': False,
                'type': 'relative',
                'value': 0.4,
            },
            'plugins': 'rabbitmq_management rabbitmq_peer_discovery_k8s',
            'extraPlugins': '',
            'loadDefinition': {
                'enabled': False,
                'existingSecret': '',
                'value': '',
            },
            'extraEnvVars': [],
            'configuration': '',
            'extraConfiguration': '',
            'serviceAccount': {
                'create': True,
                'name': '',
            },
            'livenessProbe': {
                'enabled': True,
                'initialDelaySeconds': 120,
                'timeoutSeconds': 20,
                'periodSeconds': 30,
                'failureThreshold': 6,
                'successThreshold': 1,
            },
            'readinessProbe': {
                'enabled': True,
                'initialDelaySeconds': 10,
                'timeoutSeconds': 20,
                'periodSeconds': 30,
                'failureThreshold': 3,
                'successThreshold': 1,
            },
            'rbac': {
                'create': True,
            },
            'persistence': {
                'enabled': True,
                'storageClass': '-',
                'selector': {},
                'accessMode': 'ReadWriteOnce',
                'existingClaim': '',
                'size': '8Gi',
            },
            'service': {
                'type': 'ClusterIP',
                'port': 5672,
                'portName': 'amqp',
                'tlsPort': 5671,
                'tlsPortName': 'amqp-ssl',
                'managerPort': 15672,
                'managerPortName': 'http-stats',
                'metricsPort': 15692,
                'metricsPortName': 'metrics',
                'epmdPort': 4369,
                'epmdPortName': 'epmd',
            },
            'metrics': {
                'enabled': False,
                'plugins': 'rabbitmq_prometheus',
                'podAnnotations': {
                    'prometheus.io/scrape': 'true',
                    'prometheus.io/port': OptionValue('service.metricsPort', wrap_type=str),
                },
                'serviceMonitor': {
                    'enabled': False,
                    'interval': '30s',
                }
            },
            'resources': None,
        }

    def name_format(self, suffix: str = ''):
        ret = self.releasename
        if suffix != '':
            ret = '{}-{}'.format(ret, suffix)
        return ret

    def generate(self) -> Chart:
        namespace_value = ValueData(self.namespace, enabled=self.namespace is not None)

        data: List[ChartData] = []

        if self._options.option_get('serviceAccount.create'):
            data.append({
                'apiVersion': 'v1',
                'kind': 'ServiceAccount',
                'metadata': {
                    'name': self._serviceaccount,
                    'namespace': namespace_value,
                }
            })

        if self._options.option_get('rbac.create'):
            data.extend([
                {
                    'kind': 'Role',
                    'apiVersion': 'rbac.authorization.k8s.io/v1beta1',
                    'metadata': {
                        'name': self.name_format(),
                        'namespace': namespace_value,
                    },
                    'rules': [{'apiGroups': [''], 'resources': ['endpoints'], 'verbs': ['get']},
                        {'apiGroups': [''], 'resources': ['events'], 'verbs': ['create']}]
                },
                {
                    'kind': 'RoleBinding',
                    'apiVersion': 'rbac.authorization.k8s.io/v1beta1',
                    'metadata': {
                        'name': self.name_format(),
                        'namespace': namespace_value,
                    },
                    'subjects': [{
                        'kind': 'ServiceAccount',
                        'name': self._serviceaccount,
                    }],
                    'roleRef': {
                        'apiGroup': 'rbac.authorization.k8s.io',
                        'kind': 'Role',
                        'name': self.name_format(),
                    }
                },
            ])

        plugins = set(self._options.option_get('plugins').split(' '))
        if self._options.option_get('extraPlugins') != '':
            plugins.update(self._options.option_get('extraPlugins').split(' '))
        if self._options.option_get('metrics.enabled'):
            plugins.add(self._options.option_get('metrics.plugins'))

        data.append({
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'metadata': {
                'name': self.name_format('config'),
                'namespace': namespace_value,
            },
            'data': {
                'enabled_plugins': '[{}].'.format(', '.join(plugins)),
                'rabbitmq.conf': KDataHelper_ConfigFile.info(self._options.option_get_opt(
                    'configuration', RabbitMQConfigFile()), self._options, [
                    ConfigFileRender_SysCtl(),
                    ConfigFileRender_RawStr()
                ]),
            }
        })

        config_secret = {}
        if self._options.option_get('auth.existingErlangSecret') == '':
            config_secret['rabbitmq-erlang-cookie'] = self._options.option_get('auth.erlangCookie')

        if self._options.option_get('loadDefinition.enabled') and self._options.option_get('loadDefinition.existingSecret') == '':
            config_secret['load_definition.json'] = self._options.option_get('loadDefinition.value')

        data.append({
            'apiVersion': 'v1',
            'kind': 'Secret',
            'metadata': {
                'name': self.name_format('config-secret'),
                'namespace': namespace_value,
            },
            'type': 'Opaque',
            'data': config_secret,
        })

        data.extend([
            {
                'apiVersion': 'v1',
                'kind': 'Service',
                'metadata': {
                    'name': self.name_format('headless'),
                    'namespace': namespace_value,
                    'labels': {
                        'app.kubernetes.io/name': 'rabbitmq',
                        'app.kubernetes.io/instance': self.name_format(),
                    },
                },
                'spec': {
                    'clusterIP': 'None',
                    'ports': [{
                        'name': 'epmd',
                        'port': 4369,
                        'protocol': 'TCP',
                        'targetPort': 4369
                    },
                    {
                        'name': 'cluster-links',
                        'port': 25672,
                        'protocol': 'TCP',
                        'targetPort': 25672
                    }],
                    'selector': {
                        'app.kubernetes.io/name': 'rabbitmq',
                        'app.kubernetes.io/instance': self.name_format(),
                    },
                    'type': 'ClusterIP',
                    'sessionAffinity': 'None'
                }
            },
            {
                'apiVersion': 'apps/v1',
                'kind': 'StatefulSet',
                'metadata': {
                    'name': self.name_format(),
                    'namespace': namespace_value,
                    'labels': {
                        'app.kubernetes.io/name': 'rabbitmq',
                        'app.kubernetes.io/instance': self.name_format(),
                    },
                },
                'spec': {
                    'selector': {
                        'matchLabels': {
                            'app.kubernetes.io/name': 'rabbitmq',
                            'app.kubernetes.io/instance': self.name_format(),
                        }
                    },
                    'serviceName': self.name_format('headless'),
                    'replicas': 1,
                    'template': {
                        'metadata': {
                            'namespace': namespace_value,
                            'labels': {
                                'app.kubernetes.io/name': 'rabbitmq',
                                'app.kubernetes.io/instance': self.name_format(),
                            },
                            'annotations': self._options.option_get('metrics.podAnnotations'),
                        },
                        'spec': {
                            'initContainers': [{
                                'name': 'rabbitmq-config',
                                'image': 'busybox:1.32.0',
                                'securityContext': {
                                    'runAsUser': 0,
                                    'runAsGroup': 0
                                },
                                'volumeMounts': [{
                                    'name': 'rabbitmq-config',
                                    'mountPath': '/tmp/rabbitmq'
                                },
                                {
                                    'name': 'rabbitmq-config-rw',
                                    'mountPath': '/etc/rabbitmq'
                                },
                                {
                                    'name': 'rabbitmq-config-erlang-cookie',
                                    'mountPath': '/tmp/rabbitmq-cookie'
                                }],
                                'command': ['sh',
                                            '-c',
                                            'cp '
                                            '/tmp/rabbitmq/rabbitmq.conf '
                                            '/etc/rabbitmq/rabbitmq.conf '
                                            "&& echo '' "
                                            '>> '
                                            '/etc/rabbitmq/rabbitmq.conf; '
                                            'cp '
                                            '/tmp/rabbitmq/enabled_plugins '
                                            '/etc/rabbitmq/enabled_plugins; '
                                            'mkdir -p '
                                            '/var/lib/rabbitmq; '
                                            'cp '
                                            '/tmp/rabbitmq-cookie/rabbitmq-erlang-cookie '
                                            '/var/lib/rabbitmq/.erlang.cookie; '
                                            'chmod 600 '
                                            '/var/lib/rabbitmq/.erlang.cookie; '
                                            'chown '
                                            '999.999 '
                                            '/etc/rabbitmq/rabbitmq.conf '
                                            '/etc/rabbitmq/enabled_plugins '
                                            '/var/lib/rabbitmq '
                                            '/var/lib/rabbitmq/.erlang.cookie']
                            }],
                            'volumes': [
                                {
                                    'name': 'rabbitmq-config',
                                    'configMap': {
                                        'name': self.name_format('config'),
                                        'optional': False,
                                        'items': [{
                                            'key': 'enabled_plugins',
                                            'path': 'enabled_plugins'
                                        },
                                        {
                                            'key': 'rabbitmq.conf',
                                            'path': 'rabbitmq.conf'
                                        }]
                                    }
                                },
                                {
                                    'name': 'rabbitmq-config-rw',
                                    'emptyDir': {}
                                },
                                {
                                    'name': 'rabbitmq-config-erlang-cookie',
                                    'secret': {
                                        'secretName': self._options.option_get_opt('auth.existingErlangSecret', self.name_format('config-secret')),
                                        'items': [{
                                            'key': 'rabbitmq-erlang-cookie',
                                            'path': 'rabbitmq-erlang-cookie',
                                        }]
                                    },
                                },
                                ValueData({
                                    'name': 'rabbitmq-config-load-definition',
                                    'secret': {
                                        'secretName': self._options.option_get_opt('loadDefinition.existingSecret', self.name_format('config-secret')),
                                        'items': [{
                                            'key': 'load_definition.json',
                                            'path': 'load_definition.json',
                                        }]
                                    },
                                }, enabled=self._options.option_get('loadDefinition.enabled')),
                                PersistenceData(name='rabbitmq-data', options=self._options),
                            ],
                            'serviceAccountName': self._serviceaccount,
                            'securityContext': {
                                'fsGroup': 999,
                                'runAsUser': 999,
                                'runAsGroup': 999
                            },
                            'containers': [{
                                'name': 'rabbitmq',
                                'image': '{}/{}:{}'.format(self._options.option_get('image.registry'),
                                                           self._options.option_get('image.repository'),
                                                           self._options.option_get('image.tag')),
                                'env': [
                                    *KDataHelper_Env.list(self._options.option_get('extraEnvVars')),
                                ],
                                'volumeMounts': [{
                                    'name': 'rabbitmq-config-rw',
                                    'mountPath': '/etc/rabbitmq'
                                },
                                {
                                    'name': 'rabbitmq-data',
                                    'mountPath': '/var/lib/rabbitmq/mnesia'
                                }, {
                                    'name': 'rabbitmq-config-load-definition',
                                    'mountPath': '/etc/rabbitmq-load-definition',
                                    'readOnly': True,
                                }],
                                'ports': [{
                                    'name': 'amqp',
                                    'containerPort': 5672,
                                    'protocol': 'TCP'
                                },
                                ValueData({
                                    'name': 'amqp-ssl',
                                    'containerPort': 5671,
                                    'protocol': 'TCP'
                                }, enabled=self._options.option_get('auth.tls.enabled')),
                                {
                                    'name': 'http-stats',
                                    'containerPort': 15672,
                                    'protocol': 'TCP'
                                },
                                {
                                    'name': 'metrics',
                                    'containerPort': 15692,
                                    'protocol': 'TCP'
                                },
                                {
                                    'name': 'epmd',
                                    'containerPort': 4369,
                                    'protocol': 'TCP'
                                }],
                                'livenessProbe': ValueData({
                                    'exec': {
                                        'command': ['rabbitmq-diagnostics', 'status']
                                    },
                                    'initialDelaySeconds': self._options.option_get('livenessProbe.initialDelaySeconds'),
                                    'periodSeconds': self._options.option_get('livenessProbe.timeoutSeconds'),
                                    'timeoutSeconds': self._options.option_get('livenessProbe.periodSeconds'),
                                    'failureThreshold': self._options.option_get('livenessProbe.failureThreshold'),
                                    'successThreshold': self._options.option_get('livenessProbe.successThreshold'),
                                }, enabled=self._options.option_get('livenessProbe.enabled')),
                                'readinessProbe': ValueData({
                                    'exec': {
                                        'command': ['rabbitmq-diagnostics', 'ping']
                                    },
                                    'initialDelaySeconds': self._options.option_get('readinessProbe.initialDelaySeconds'),
                                    'periodSeconds': self._options.option_get('readinessProbe.timeoutSeconds'),
                                    'timeoutSeconds': self._options.option_get('readinessProbe.periodSeconds'),
                                    'failureThreshold': self._options.option_get('readinessProbe.failureThreshold'),
                                    'successThreshold': self._options.option_get('readinessProbe.successThreshold'),
                                }, enabled=self._options.option_get('readinessProbe.enabled')),
                                'resources': ValueData(self._options.option_get('resources'), disabled_if_none=True),
                            }]
                        }
                    },
                    'volumeClaimTemplates': [
                        VolumeClaimTemplate(name='rabbitmq-data', options=self._options),
                    ],
                },
            },
            {
                'kind': 'Service',
                'apiVersion': 'v1',
                'metadata': {
                    'name': self.name_format('service'),
                    'namespace': namespace_value,
                    'labels': {
                        'app.kubernetes.io/name': 'rabbitmq',
                        'app.kubernetes.io/instance': self.name_format(),
                    },
                },
                'spec': {
                    'type': 'ClusterIP',
                    'ports': [{
                        'name': self._options.option_get('service.managerPortName'),
                        'protocol': 'TCP',
                        'port': self._options.option_get('service.managerPort'),
                        'targetPort': 'http-stats',
                    }, {
                        'name': self._options.option_get('service.epmdPortName'),
                        'protocol': 'TCP',
                        'port': self._options.option_get('service.epmdPort'),
                        'targetPort': 'epmd',
                    }, ValueData({
                        'name': self._options.option_get('service.metricsPortName'),
                        'protocol': 'TCP',
                        'port': self._options.option_get('service.metricsPort'),
                        'targetPort': 'metrics',
                    }, enabled=self._options.option_get('metrics.enabled')), {
                        'name': self._options.option_get('service.portName'),
                        'protocol': 'TCP',
                        'port': self._options.option_get('service.port'),
                        'targetPort': 'amqp',
                    }],
                    'selector': {
                        'app.kubernetes.io/name': 'rabbitmq',
                        'app.kubernetes.io/instance': self.name_format(),
                    }
                }
            },
        ])

        if self._options.option_get('metrics.serviceMonitor.enabled'):
            data.append({
                'apiVersion': 'monitoring.coreos.com/v1',
                'kind': 'ServiceMonitor',
                'metadata': {
                    'name': self.name_format(),
                    'namespace': namespace_value,
                    'labels': {
                        'app.kubernetes.io/name': 'rabbitmq',
                        'app.kubernetes.io/instance': self.name_format(),
                    }
                },
                'spec': {
                    'endpoints': [{
                        'port': 'metrics',
                        'interval': self._options.option_get('metrics.serviceMonitor.interval'),
                    }],
                    'namespaceSelector': {
                        'matchNames': [namespace_value]
                    },
                    'selector': {
                        'matchLabels': {
                            'app.kubernetes.io/name': 'rabbitmq',
                            'app.kubernetes.io/instance': self.name_format(),
                        }
                    }
                }
            })

        return RabbitMQChart(request=self, config=self.config,
                             data=OptionsBuildData(self._options, data))


class RabbitMQChart(Chart):
    request: RabbitMQChartRequest

    def __init__(self, request: RabbitMQChartRequest, config: Optional[Config] = None,
                 data: Optional[Sequence[ChartData]] = None):
        super().__init__(config=config, data=data)
        self.request = request

    def createClone(self) -> 'Chart':
        return RabbitMQChart(request=self.request, config=self.config)

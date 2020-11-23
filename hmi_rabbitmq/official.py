from typing import Optional, Mapping, Any, Sequence, List

import deepmerge  # type: ignore
from helmion.chart import Chart
from helmion.config import Config
from helmion.data import ChartData
from kubragen2.build import ValueData, BuildData
from kubragen2.options import Options, OptionValue, OptionsBuildData


class RabbitMQOfficialRequest:
    """
    Based on `rabbitmq/diy-kubernetes-examples <https://github.com/rabbitmq/diy-kubernetes-examples>`_.
    """
    config: Config
    namespace: Optional[str]
    releasename: str
    values: Optional[Mapping[str, Any]]

    def __init__(self, namespace: Optional[str] = 'default', releasename: str = 'rabbitmq',
                 values: Optional[Mapping[str, Any]] = None, config: Optional[Config] = None):
        self.namespace = namespace
        self.releasename = releasename
        self.values = values
        self.config = config if config is not None else Config()

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
                'volumes': {},
            },
            'service': {
                'type': 'ClusterIP',
                'port': '5672',
                'portName': 'amqp',
                'tlsPort': '5671',
                'tlsPortName': 'amqp-ssl',
                'distPort': '25672',
                'distPortName': 'dist',
                'managerPort': '15672',
                'managerPortName': 'http-stats',
                'metricsPort': '9419',
                'metricsPortName': 'metrics',
            },
            'metrics': {
                'enabled': False,
                'plugins': 'rabbitmq_prometheus',
                'podAnnotations': {
                    'prometheus.io/scrape': '"true"',
                    'prometheus.io/port': OptionValue('service.metricsPort'),
                },
                'serviceMonitor': {
                    'enabled': False,
                    'interval': '30s',
                }
            },
            'resources': {},
        }

    def object_name(self, suffix: str = ''):
        ret = self.releasename
        if suffix != '':
            ret = '{}-{}'.format(ret, suffix)
        return ret

    def generate(self) -> Chart:
        values = Options(self.allowedValues(), self.values)
        # values = deepmerge.merge_or_raise.merge(self.allowedValues(), self.values)

        serviceaccount = values.option_get_opt('serviceAccount.name', self.object_name())
        namespace_value = ValueData(self.namespace, enabled=self.namespace is not None)

        data: List[ChartData] = []

        if values.option_get('serviceAccount.create'):
            data.append({
                'apiVersion': 'v1',
                'kind': 'ServiceAccount',
                'metadata': {
                    'name': serviceaccount,
                    'namespace': namespace_value,
                }
            })

        if values.option_get('rbac.create'):
            data.extend([
                {
                    'kind': 'Role',
                    'apiVersion': 'rbac.authorization.k8s.io/v1beta1',
                    'metadata': {
                        'name': self.object_name(),
                        'namespace': namespace_value,
                    },
                    'rules': [{'apiGroups': [''], 'resources': ['endpoints'], 'verbs': ['get']},
                        {'apiGroups': [''], 'resources': ['events'], 'verbs': ['create']}]
                },
                {
                    'kind': 'RoleBinding',
                    'apiVersion': 'rbac.authorization.k8s.io/v1beta1',
                    'metadata': {
                        'name': self.object_name(),
                        'namespace': namespace_value,
                    },
                    'subjects': [{
                        'kind': 'ServiceAccount',
                        'name': serviceaccount,
                    }],
                    'roleRef': {
                        'apiGroup': 'rbac.authorization.k8s.io',
                        'kind': 'Role',
                        'name': self.object_name(),
                    }
                },
            ])

        plugins = set(values.option_get('plugins').split(' '))
        if values.option_get('extraPlugins') != '':
            plugins.update(values.option_get('extraPlugins').split(' '))

        data.append({
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'metadata': {
                'name': self.object_name('config'),
                'namespace': namespace_value,
            },
            'data': {
                'enabled_plugins': ' '.join(plugins),
                'rabbitmq.conf': self.configfile_get(values),
            }
        })

        config_secret = {}
        if values.option_get('auth.existingErlangSecret') == '':
            config_secret['rabbitmq-erlang-cookie'] = values.option_get('auth.erlangCookie')

        if values.option_get('loadDefinition.enabled') and values.option_get('loadDefinition.existingSecret') == '':
            config_secret['load_definition.json'] = values.option_get('loadDefinition.value')

        data.append({
            'apiVersion': 'v1',
            'kind': 'Secret',
            'metadata': {
                'name': self.object_name('config-secret'),
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
                    'name': self.object_name('headless'),
                    'namespace': namespace_value,
                    'labels': {
                        'app.kubernetes.io/name': 'rabbitmq',
                        'app.kubernetes.io/instance': self.object_name(),
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
                        'app.kubernetes.io/instance': self.object_name(),
                    },
                    'type': 'ClusterIP',
                    'sessionAffinity': 'None'
                }
            },
            {
                'apiVersion': 'apps/v1',
                'kind': 'StatefulSet',
                'metadata': {
                    'name': self.object_name(),
                    'namespace': namespace_value,
                    'labels': {
                        'app.kubernetes.io/name': 'rabbitmq',
                        'app.kubernetes.io/instance': self.object_name(),
                    },
                },
                'spec': {
                    'selector': {
                        'matchLabels': {
                            'app.kubernetes.io/name': 'rabbitmq',
                            'app.kubernetes.io/instance': self.object_name(),
                        }
                    },
                    'serviceName': self.object_name('headless'),
                    'replicas': 1,
                    'template': {
                        'metadata': {
                            'namespace': namespace_value,
                            'labels': {
                                'app.kubernetes.io/name': 'rabbitmq',
                                'app.kubernetes.io/instance': self.object_name(),
                            },
                            'annotations': values.option_get('metrics.podAnnotations'),
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
                                            '/tmp/rabbitmq-cookie/erlang_cookie '
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
                                        'name': self.object_name('config'),
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
                                        'secretName': values.option_get_opt('auth.existingErlangSecret', self.object_name('config-secret')),
                                        'items': [{
                                            'key': 'rabbitmq-erlang-cookie',
                                            'path': 'rabbitmq-erlang-cookie',
                                        }]
                                    },
                                },
                                ValueData({
                                    'name': 'rabbitmq-config-load-definition',
                                    'secret': {
                                        'secretName': values.option_get_opt('loadDefinition.existingSecret', self.object_name('config-secret')),
                                        'items': [{
                                            'key': 'load_definition.json',
                                            'path': 'load_definition.json',
                                        }]
                                    },
                                }, enabled=values.option_get('loadDefinition.enabled')),
                                {
                                    'name': 'rabbitmq-data',
                                    'persistentVolumeClaim': {
                                        'claimName': values.option_get('persistence.existingClaim'),
                                    },
                                },
                            ],
                            'serviceAccountName': serviceaccount,
                            'securityContext': {
                                'fsGroup': 999,
                                'runAsUser': 999,
                                'runAsGroup': 999
                            },
                            'containers': [{
                                'name': 'rabbitmq',
                                'image': '{}/{}:{}'.format(values.option_get('image.registry'),
                                                           values.option_get('image.repository'),
                                                           values.option_get('image.tag')),
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
                                {
                                    'name': 'management',
                                    'containerPort': 15672,
                                    'protocol': 'TCP'
                                },
                                {
                                    'name': 'prometheus',
                                    'containerPort': 15692,
                                    'protocol': 'TCP'
                                },
                                {
                                    'name': 'epmd',
                                    'containerPort': 4369,
                                    'protocol': 'TCP'
                                }],
                                'livenessProbe': {
                                    'exec': {
                                        'command': ['rabbitmq-diagnostics', 'status']
                                    },
                                    'initialDelaySeconds': 120,
                                    'periodSeconds': 30,
                                    'timeoutSeconds': 20,
                                    'failureThreshold': 6,
                                    'successThreshold': 1,
                                },
                                'readinessProbe': {
                                    'exec': {
                                        'command': ['rabbitmq-diagnostics', 'ping']
                                    },
                                    'initialDelaySeconds': 10,
                                    'periodSeconds': 30,
                                    'timeoutSeconds': 20,
                                    'failureThreshold': 3,
                                    'successThreshold': 1,
                                },
                                'resources': ValueData(value=values.option_get('resources'), disabled_if_none=True),
                            }]
                        }
                    },
                }
            },
            {
                'kind': 'Service',
                'apiVersion': 'v1',
                'metadata': {
                    'name': self.object_name('service'),
                    'namespace': namespace_value,
                    'labels': {
                        'app.kubernetes.io/name': 'rabbitmq',
                        'app.kubernetes.io/instance': self.object_name(),
                    },
                },
                'spec': {
                    'type': 'ClusterIP',
                    'ports': [{
                        'name': 'http',
                        'protocol': 'TCP',
                        'port': 15672,
                    }, ValueData({
                        'name': 'prometheus',
                        'protocol': 'TCP',
                        'port': 15692
                    }, enabled=values.option_get('metrics.enabled')), {
                        'name': 'amqp',
                        'protocol': 'TCP',
                        'port': 5672
                    }],
                    'selector': {
                        'app.kubernetes.io/name': 'rabbitmq',
                        'app.kubernetes.io/instance': self.object_name(),
                    }
                }
            },
        ])

        return RabbitMQOfficialChart(request=self, config=self.config, data=OptionsBuildData(values, data))


    def configfile_get(self, values: Options):
        ret = []

        ret.append('default_user = {}'.format(values.option_get('auth.username')))
        ret.append('default_pass = {}'.format(values.option_get('auth.password')))
        ret.append('cluster_formation.peer_discovery_backend  = rabbit_peer_discovery_k8s')
        ret.append('cluster_formation.k8s.host = kubernetes.default.svc.{}'.format(values.option_get('clusterDomain')))
        ret.append('cluster_formation.node_cleanup.interval = 10')
        ret.append('cluster_formation.node_cleanup.only_log_warning = true')
        ret.append('cluster_partition_handling = autoheal')
        ret.append('queue_master_locator = min-masters')
        ret.append('loopback_users.guest = false')
        if values.option_get('extraConfiguration') != '':
            for c in values.option_get('extraConfiguration').split('\n'):
                ret.append(c)
        if values.option_get('auth.tls.enabled'):
            ret.append('ssl_options.verify = {}'.format(values.option_get('auth.tls.sslOptionsVerify')))
            ret.append('listeners.ssl.default = {}'.format(values.option_get('service.tlsPort')))
            ret.append('ssl_options.fail_if_no_peer_cert = {}'.format(values.option_get('auth.tls.failIfNoPeerCert')))
            ret.append('ssl_options.cacertfile = /opt/bitnami/rabbitmq/certs/ca_certificate.pem')
            ret.append('ssl_options.certfile = /opt/bitnami/rabbitmq/certs/server_certificate.pem')
            ret.append('ssl_options.keyfile = /opt/bitnami/rabbitmq/certs/server_key.pem')
        if values.option_get('metrics.enabled'):
            ret.append('prometheus.tcp.port = 9419')
        if values.option_get('memoryHighWatermark.enabled'):
            ret.append('total_memory_available_override_value = {}'.format(values.option_get_opt('resources.limits.memory', '100Mi')))
            ret.append('vm_memory_high_watermark.{} = {}'.format(values.option_get('memoryHighWatermark.type'),
                                                                 values.option_get('memoryHighWatermark.value')))
        return '\n'.join(ret)


class RabbitMQOfficialChart(Chart):
    request: RabbitMQOfficialRequest

    def __init__(self, request: RabbitMQOfficialRequest, config: Optional[Config] = None,
                 data: Optional[Sequence[ChartData]] = None):
        super().__init__(config=config, data=data)
        self.request = request

    def createClone(self) -> 'Chart':
        return RabbitMQOfficialChart(request=self.request, config=self.config)

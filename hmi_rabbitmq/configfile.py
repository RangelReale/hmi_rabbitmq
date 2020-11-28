from typing import Optional, Sequence, Mapping, Any, Dict

from kubragen2.configfile import ConfigFile_Extend, ConfigFileExtension, ConfigFileExtensionData, ConfigFileOutput, \
    ConfigFileOutput_Dict
from kubragen2.options import Options, optionsmerger


class RabbitMQConfigFile(ConfigFile_Extend):
    merge_config: Optional[Mapping[Any, Any]]

    def __init__(self, merge_config: Optional[Mapping[Any, Any]] = None,
                 extensions: Optional[Sequence[ConfigFileExtension]] = None):
        super().__init__(extensions)
        self.merge_config = merge_config

    def init_value(self, options: Options) -> ConfigFileExtensionData:
        config: Dict[Any, Any] = {}

        config['default_user'] = options.option_get('auth.username')
        config['default_pass'] = options.option_get('auth.password')
        if 'rabbitmq_peer_discovery_k8s' in options.option_get('plugins').split(' '):
            config['cluster_formation.peer_discovery_backend'] = 'rabbit_peer_discovery_k8s'
            config['cluster_formation.k8s.host'] = 'kubernetes.default.svc.{}'.format(options.option_get('clusterDomain'))
            config['cluster_formation.node_cleanup.interval'] = 10
            config['cluster_formation.node_cleanup.only_log_warning'] = 'true'
            config['cluster_partition_handling'] = 'autoheal'
        config['queue_master_locator'] = 'min-masters'
        config['loopback_users.guest'] = 'false'
        if options.option_get('auth.tls.enabled'):
            config['ssl_options.verify'] = options.option_get('auth.tls.sslOptionsVerify')
            config['listeners.ssl.default'] = options.option_get('service.tlsPort')
            config['ssl_options.fail_if_no_peer_cert'] = options.option_get('auth.tls.failIfNoPeerCert')
            config['ssl_options.cacertfile'] = '/opt/bitnami/rabbitmq/certs/ca_certificate.pem'
            config['ssl_options.certfile'] = '/opt/bitnami/rabbitmq/certs/server_certificate.pem'
            config['ssl_options.keyfile'] = '/opt/bitnami/rabbitmq/certs/server_key.pem'
        if options.option_get('loadDefinition.enabled') is not None:
            config['load_definitions'] = '/etc/rabbitmq-load-definition/load_definition.json'
        if options.option_get('metrics.enabled'):
            config['prometheus.tcp.port'] = options.option_get('service.metricsPort')
        if options.option_get('memoryHighWatermark.enabled'):
            config['total_memory_available_override_value'] = options.option_get_opt('resources.limits.memory', '100Mi')
            config['vm_memory_high_watermark.{}'.format(
                options.option_get('memoryHighWatermark.type'))] = options.option_get('memoryHighWatermark.value')
        if options.option_get('extraConfiguration') != '':
            for c in options.option_get('extraConfiguration').split('\n'):
                cv = c.split('=')
                config[cv[0]] = cv[1]
        return ConfigFileExtensionData(config)

    def finish_value(self, options: Options, data: ConfigFileExtensionData) -> ConfigFileOutput:
        if self.merge_config is not None:
            optionsmerger.merge(data.data, self.merge_config)
        return ConfigFileOutput_Dict(data.data)

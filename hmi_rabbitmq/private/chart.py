from typing import Any, Dict

from kubragen2.data import Data
from kubragen2.options import Options


class PersistenceData(Data):
    name: str
    options: Options

    def __init__(self, name: str, options: Options):
        self.options = options
        self.name = name

    def is_enabled(self) -> bool:
        return self.options.option_get('persistence.enabled') and \
               self.options.option_get('persistence.existingClaim') != ''

    def get_value(self) -> Any:
        ret: Dict[Any, Any] = {
            'name': self.name,
        }
        if self.options.option_get('persistence.enabled') and self.options.option_get('persistence.existingClaim') != '':
            ret['persistentVolumeClaim'] = {
                'claimName': self.options.option_get('persistence.existingClaim'),
            }
        else:
            ret['emptyDir'] = {}
        return ret


class VolumeClaimTemplate(Data):
    name: str
    options: Options

    def __init__(self, name: str, options: Options):
        self.options = options
        self.name = name

    def is_enabled(self) -> bool:
        return self.options.option_get('persistence.enabled') and \
               self.options.option_get('persistence.existingClaim') == ''

    def get_value(self) -> Any:
        return {
            'metadata': {
                'name': self.name,
                'labels': {
                    'app.kubernetes.io/name': 'rabbitmq',
                    'app.kubernetes.io/instance': self.options.option_get('base.releasename'),
                },
            },
            'spec': {
                'accessModes': [
                    self.options.option_get('persistence.accessMode'),
                ],
                'resources': {
                    'requests': {
                        'storage': self.options.option_get('persistence.size'),
                    },
                },
                'storageClass': self.options.option_get_opt_custom('persistence.storageClass', '', [None, '', '-']),
                'selector': self.options.option_get('persistence.selector'),
            }
        }

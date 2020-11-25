# Helmion Plugin: RabbitMQ

[![PyPI version](https://img.shields.io/pypi/v/hmi_rabbitmq.svg)](https://pypi.python.org/pypi/hmi_rabbitmq/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/hmi_rabbitmq.svg)](https://pypi.python.org/pypi/hmi_rabbitmq/)

hmi_rabbitmqchart generator for [Helmion](https://github.com/RangelReale/helmion) that deploys 
a [RabbitMQ](https://www.rabbitmq.com/) server in Kubernetes.

Helmion is a python library to download and customize [Helm](https://helm.sh/) charts, and can
also be used to generate custom charts.

* Website: https://github.com/RangelReale/hmi_rabbitmq
* Repository: https://github.com/RangelReale/hmi_rabbitmq.git
* Documentation: https://hmi_rabbitmq.readthedocs.org/
* PyPI: https://pypi.python.org/pypi/hmi_rabbitmq

## Example

```python
from kubragen2.output import OutputProject, OutputFile_ShellScript, OutputFile_Kubernetes, OD_FileTemplate, \
    OutputDriver_Print

from hmi_rabbitmq import RabbitMQChartRequest, RabbitMQConfigFile

out = OutputProject()

shell_script = OutputFile_ShellScript('create_gke.sh')
out.append(shell_script)

shell_script.append('set -e')

#
# OUTPUTFILE: app-namespace.yaml
#
file = OutputFile_Kubernetes('app-namespace.yaml')

file.append([
    {
        'apiVersion': 'v1',
        'kind': 'Namespace',
        'metadata': {
            'name': 'app-monitoring',
        },
    }
])

out.append(file)
shell_script.append(OD_FileTemplate(f'kubectl apply -f ${{FILE_{file.fileid}}}'))

shell_script.append(f'kubectl config set-context --current --namespace=app-monitoring')


#
# SETUP: rabbitmq
#
rabbitmq_req = RabbitMQChartRequest(namespace='app-monitoring', releasename='myrabbitmq', values={
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

rabbitmq_chart = rabbitmq_req.generate()

#
# OUTPUTFILE: rabbitmq.yaml
#
file = OutputFile_Kubernetes('rabbitmq.yaml')
out.append(file)

file.append(rabbitmq_chart.data)

shell_script.append(OD_FileTemplate(f'kubectl apply -f ${{FILE_{file.fileid}}}'))

#
# Write files
#
out.output(OutputDriver_Print())
# out.output(OutputDriver_Directory('/tmp/build-gke'))
```

Output:

```text
****** BEGIN FILE: 001-app-namespace.yaml ********
apiVersion: v1
kind: Namespace
metadata:
  name: app-monitoring

****** END FILE: 001-app-namespace.yaml ********
****** BEGIN FILE: 002-rabbitmq.yaml ********
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myrabbitmq
  namespace: app-monitoring
---
kind: Role
apiVersion: rbac.authorization.k8s.io/v1beta1
metadata:
  name: myrabbitmq
  namespace: app-monitoring
rules:
- apiGroups:
  - ''
  resources:
  - endpoints
  verbs:
  - get
- apiGroups:
  - ''
  resources:
  - events
  verbs:
  - create
---
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1beta1
metadata:
  name: myrabbitmq
  namespace: app-monitoring
subjects:
- kind: ServiceAccount
  name: myrabbitmq
<...more...>

****** END FILE: 002-rabbitmq.yaml ********
****** BEGIN FILE: create_gke.sh ********
#!/bin/bash

set -e
kubectl apply -f 001-app-namespace.yaml
kubectl config set-context --current --namespace=app-monitoring
kubectl apply -f 002-rabbitmq.yaml

****** END FILE: create_gke.sh ********
```

## Author

Rangel Reale (rangelreale@gmail.com)

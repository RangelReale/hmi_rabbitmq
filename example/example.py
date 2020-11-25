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

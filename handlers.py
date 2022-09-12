import kopf
import kubernetes
import yaml


@kopf.on.create('hyperflow.agh.edu.pl', 'v1', 'workerpools')
def create_fn(body, spec, **kwargs):
    name = body['metadata']['name']
    namespace = body['metadata']['namespace']
    queue_name = body['metadata']['namespace'] + '.' + spec['taskType']

    deployment = get_deployment(name, namespace, queue_name, spec)
    prometheus_rule = get_prometheus_rule(name, namespace, queue_name, spec)
    hpa = get_hpa(name, namespace, queue_name)

    kopf.adopt(deployment, owner=body)
    kopf.adopt(prometheus_rule, owner=body)
    kopf.adopt(hpa, owner=body)

    apps_api = kubernetes.client.AppsV1Api()
    crd_api = kubernetes.client.CustomObjectsApi()

    obj = apps_api.create_namespaced_deployment(namespace, deployment)
    print(f"Deployment {obj.metadata.name} created")

    obj = crd_api.create_namespaced_custom_object(group="monitoring.coreos.com",
                                                  version="v1",
                                                  namespace=namespace,
                                                  plural="prometheusrules",
                                                  body=prometheus_rule)
    print(f"PrometheusRule {obj} created")

    obj = crd_api.create_namespaced_custom_object(group="keda.sh",
                                                  version="v1alpha1",
                                                  namespace=namespace,
                                                  plural="scaledobjects",
                                                  body=hpa)
    print(f"HPA {obj.metadata.name} created")

    msg = f"Worker pool {name} deployment created"
    return {'message': msg}


def get_deployment(name, namespace, queue_name, spec):
    with open(r'/templates/deployment.yml') as file:
        image = spec['image']
        cpu_requests = spec['initialResources']['requests']['cpu']
        memory_requests = spec['initialResources']['requests']['memory']
        cpu_limits = spec['initialResources']['limits']['cpu']
        memory_limits = spec['initialResources']['limits']['memory']
        template = file.read().format(poolName=name,
                                      namespace=namespace,
                                      image=image,
                                      queueName=queue_name,
                                      cpuRequests=cpu_requests,
                                      memoryRequests=memory_requests,
                                      cpuLimits=cpu_limits,
                                      memoryLimits=memory_limits)
        return yaml.safe_load(template)


def get_prometheus_rule(name, namespace, queue_name, spec):
    cpu_limits = spec['initialResources']['limits']['cpu']
    memory_limits = spec['initialResources']['limits']['memory']
    with open(r'/templates/prometheus-rule.yml') as file:
        template = file.read().format(poolName=name,
                                      namespace=namespace,
                                      queueName=queue_name,
                                      poolNameUnderscored=name.replace('-', '_'),
                                      cpuLimits=cpu_limits,
                                      memoryLimits=memory_limits)
        return yaml.safe_load(template)


def get_hpa(name, namespace, queue_name):
    with open(r'/templates/scaledobject.yml') as file:
        template = file.read().format(poolName=name,
                                      namespace=namespace,
                                      queueName=queue_name,
                                      poolNameUnderscored=name.replace('-', '_'))
        return yaml.safe_load(template)


@kopf.on.create('hyperflow.agh.edu.pl', 'v1', 'workerpools')
def delete(body, **kwargs):
    msg = f"Worker pool {body['metadata']['name']} and children deleted"
    return {'message': msg}

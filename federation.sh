#!/usr/bin/env bash

function setupUpstreamsOnRabbitmq01()
{
    # 通过rabbitmq的parameter新增upstream，json格式参数的key参见：https://www.rabbitmq.com/federation-reference.html
    rabbitmqctl set_parameter federation-upstream upstream_rabbitmq02 '{"uri": "amqp://guest:guest@rabbitmq02/%2f", "prefetch-count": 10000, "reconnect-delay": 1, "ack-mode": "on-confirm", "trust-user-id": false, "max-hops": 100, "ha-policy": "all"}'
    rabbitmqctl set_parameter federation-upstream upstream_rabbitmq03 '{"uri": "amqp://guest:guest@rabbitmq03/%2f", "prefetch-count": 10000, "reconnect-delay": 1, "ack-mode": "on-confirm", "trust-user-id": false, "max-hops": 100, "ha-policy": "all"}'
}

function setupUpstreamSetsRabbitmq01()
{
    # 添加upstream set
    rabbitmqctl set_parameter federation-upstream-set upstream_set_on_rabbitmq01 '[{"upstream": "upstream_rabbitmq02"}, {"upstream": "upstream_rabbitmq03"}]'
}

function setupPolicies()
{
    # rabbitmqctl set_policy upstream_rabbitmq02 'nova' '{"federation-upstream": "upstream_rabbitmq02"}' --apply-to exchanges --priority 10
    rabbitmqctl set_policy federation_on_rabbitmq01 'nova' '{"federation-upstream-set": "upstream_set_on_rabbitmq01"}' --apply-to exchanges --priority 10

}

# 这样的话，计算节点之间的 rpc cast/fanout_cast 就好处理了
# rpc call 怎么办？default direct exchange 可以被 federated 吗？（default exchange 不能被 federated）
# 为 rpc call 建立一个专门的 callback exchange，类型：direct。将此 exchange 设置为 federated。rpc call 发起调用时，只需要创建 reply_msg_id，并将之帮定在该 exchange 上即可。
# 被调用者只需要，回复 rpc call 到该 exchange 即可。
# 之前的 rpc call 调用是先建立 callback exchange：reply_msg_id，然后将 queue：reply_msg_id 绑定在之上。
# 资料：
# RabbitMQ中文文档：http://rabbitmq.mr-ping.com
# Distributed log aggregation with RabbitMQ Federation：https://jaxenter.com/distributed-log-aggregation-with-rabbitmq-federation-107287.html
# 深度解析RabbitMQ集群：http://www.iteye.com/news/31429
# 官网对Federation的介绍：http://www.rabbitmq.com/federation.html
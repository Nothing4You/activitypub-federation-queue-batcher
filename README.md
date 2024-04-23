# activitypub-federation-queue-batcher

- it is highly recommended to pin specific container tags and not use the `latest` tag
- you'll probably want to run an instance of inbox-receiver and batch-sender for each sending instance where you need to speed up federation
  - each set will need its own `RABBITMQ_CHANNEL_ROUTING_KEY` defined
- a single batch-receiver can handle multiple batch senders
- don't run multiple batch-sender instances with the same `RABBITMQ_CHANNEL_ROUTING_KEY` or you'll get activities out of order
- preliminary validation of traffic is strongly recommended to ensure it doesn't lock up
- Activities without id will not be accepted, instead 503 Service Unavailable will be returned.
  This is a safety measure to avoid dropping such activities should we ever encounter them.
  Lemmy does not appear to support activities without id, but [the specification](https://www.w3.org/TR/activitypub/#server-to-server-interactions) seems to allow them in some cases.

```mermaid
sequenceDiagram
    autonumber

    box transparent Activity sender
    actor source as Lemmy.World
    end
    box transparent Intermediate receiver
    participant intermediate-proxy as nginx/Caddy/etc
    participant inbox-receiver
    participant rabbitmq
    end

    source->>inbox-receiver: POST /inbox

    inbox-receiver->>rabbitmq: Get queued message count
    rabbitmq->>inbox-receiver: Queued message count

    alt buffer is below limit
        inbox-receiver->>rabbitmq: Queue activity message
        rabbitmq->>inbox-receiver: Confirm publishing
        inbox-receiver->>source: 204 No Content
    else buffer is above limit
        destroy source
        inbox-receiver->>source: 503 Service Unavailable
    end
```

```mermaid
sequenceDiagram
    autonumber

    box transparent Intermediate receiver
    participant rabbitmq
    participant batch-sender
    end
    box transparent Receiving instance
    participant origin-nginx as nginx/haproxy/etc
    participant batch-receiver
    actor destination as 1.federated.test.lem.rocks
    end

    loop
        batch-sender->>rabbitmq: Get messages

        alt no messages available
            rabbitmq->>batch-sender: Queue empty
        else messages available
            break
                rabbitmq->>batch-sender: Return messages
            end
        end
    end

    batch-sender->>batch-receiver: POST /batch multiple activities

    loop each message in body
        batch-receiver->>destination: POST /inbox
        destination->>batch-receiver: 200 OK/400 Bad Request/etc

        alt 408, 429 or 5xx status
            break
                batch-receiver->>batch-sender: 500 Internal Server Error
            end
        end
    end

    batch-receiver->>batch-sender: 200 OK
    batch-sender->>batch-sender: validate subrequest status codes

    alt valid status codes for all subrequests
        batch-sender->>rabbitmq: ack all messages in batch
    else otherwise
        batch-sender->>rabbitmq: nack all messages in batch
        batch-sender->>batch-sender: exit service to ensure clean start for next attempt
    end
```

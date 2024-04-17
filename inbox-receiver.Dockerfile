ARG BASE_IMAGE
FROM $BASE_IMAGE
ENTRYPOINT ["python", "-m", "activitypub_federation_queue_batcher.inbox_receiver"]

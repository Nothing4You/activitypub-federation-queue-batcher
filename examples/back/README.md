# This example is built around lemmy-ansible.

In this example we intercept `/batch` on the Lemmy domain, which is not currently used by Lemmy.

In `nginx_internal.conf`, insert the following snippet in the `server {}` section:

```nginx
set $batch "batch-receiver:8080";
location = /batch {
    proxy_pass "http://$batch";
}
```

The block in `docker-compose-yml` can be integrated with lemmy-ansible's configuration or used standalone.

Only a single batch-receiver is needed and it can handle multiple batch-sender instances.

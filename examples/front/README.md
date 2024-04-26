The example ansible playbook will try to install a Let's Encrypt certificate.
This will fail if you don't have your instance domain pointing to this server.

You will have to implement your own certificate logic, e.g. by using DNS validation or
shipping a certificate without automatic updates.

The example is built with the following scenario in mind:

Your instance keeps running as usual. You deploy this queue close to an instance with a
large backlog of activities to send to you. Once the queue server is deployed, you have
the operator of the sending instance set up a DNS override for your instance domain to
go through this queue/proxy machine.

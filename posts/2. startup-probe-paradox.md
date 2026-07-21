---
title: "The Startup Probe Paradox: Notes on Kubernetes Probes"
date: "2026-01-10"
slug: "startup-probe-paradox"
tags: "Essay | Kubernetes"
---

Let us imagine an application running on Kubernetes that has the following characteristics:

* The application takes 300-600 seconds upon a fresh startup to become ready. 

* Once running, you want fast detection of failures. An unresponsive pod should be restarted quickly. 

An example of such a workload would be [Thanos Store Gateway](https://thanos.io/tip/components/store.md/#store). 
The Storegateway pods usually have a lot of data to read from a remote storage before they are ready to serve the [Thanos Querier](https://thanos.io/tip/components/query.md/#querierquery). 

How would one configure Kubernetes health probes for this workload?

## Kubernetes Health Checks (Probes)

Kubernetes supports three types of probes:

- *startupProbe*: If configured, Kubernetes does not execute liveness or readyness probes until this probe succeeds. The probe is evaluated only at startup and is intended to allows applications enough time to initialize. If the probe fails, Kubernetes will kill the container.
- *readinessProbe*: This probe tells Kubernetes whether a container is 'ready' to receive traffic. If this probe fails, Kubernetes removes the pod from service (ie it does not recieve any traffic) but does not restart it.
- *livenessProbe*: This probe tells Kubernetes whether a container is 'alive'. If this probe fails, Kubernetes will restart the container. 

### Workload Characteristics

Notice that the workload has two conflicting characteristics:

- A slow, stateful startup
- A need for fast failure detection once running

The ideal configuration pairs a patient, forgiving startupProbe with an aggressive livenessProbe to meet these conflicting requirements.

## Configuration

### Wait for startup with a startupProbe
The application can expose a single /ready endpoint that reports whether it is fully initialised.

A startupProbe configured against this endpoint allows the application to take its full 300–600 seconds to initialise without being penalised. While the startup probe is failing, Kubernetes will not evaluate liveness or readiness, preventing premature restarts.

### Failing fast with a livenessProbe

Once startup succeeds, to facilitate fast detection of genuine failures, a relatively aggressive livenessProbe can be configured so that if the process becomes unresponsive, the pod is restarted quickly.

### Failover gracefully using a readynessProbe
Finally, a readinessProbe can be configured that hits the same /ready endpoint, but is evaluated continuously once startup has completed.

During startup, that endpoint naturally reports “not ready”. After startup succeeds, the readiness probe ensures the pod is only included when it can actually serve traffic, and is cleanly removed during partial failures or degraded states without triggering restarts.

### A Note on initialDelaySeconds 

Although it is tempting to use `initialDelaySeconds` to ask the probe's to wait until the pods are ready, this is still sub-optinmal because n `initialDelaySeconds` forces you to guess how long initialisation might take. In this case, startup time varies widely (300–600 seconds). Any fixed delay risks being either too short, causing restart loops or unnecessarily long, masking real failures.


---
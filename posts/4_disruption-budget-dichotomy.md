---
title: "The Disruption Budget Dichotomy: How PDBs help you negotiate Availability"
date: "2026-02-22"
slug: "disruption-budget-dichotomy"
tags: "Essay | Kubernetes"
---

These are my notes on Pod Disruption Budgets (PDBs). Why? Because there are a couple of gotchas in there that I wanted to understand better. 

 -- Inspired by a painful experience I had while configuring PDBs for a production workload :P

Ok, Here we go!

## Types of Disruptions

In Kubernetes, there are two types of disruptions. The first class of disruptions are **Involuntary disruptions**. These are unavoidable disruptions which include:

- Hardware failure/VM failure or deletion
- A kernel panic
- Node disruption due to network partition
- Eviction of a pod due to node-pressure

The PodDisruptionBudget is not applicable for any of these disruptions.

The second class of disruptions are called **Voluntary disruptions**. Voluntary disruptions include:

- Those initiated by application devs like updating/deleting deployment (or pod)
- Those initiated by a cluster administrator (human or automation) like draining a node or pre-empting a pod to make room for something else

For these cases, a PodDisruptionBudget can be used to limit how many pods can be evicted/disrupted at one time.

## minAvailable and maxUnavailable
A PodDisruptionBudget can be expressed by either minAvailable or maxUnavailable settings.

- **minAvailable** specifies how many pods must remain available after an eviction
- **maxUnavailable** specifies how many pods may be unavailable after an eviction.

Both of these can be expressed as absolute numbers or a percentage (of the desired number of replicas). Let’s take a look at the disruption controller code to understand how this works.

The below code snippet shows the `getExpectedPodCount` function which returns the `desiredHealthy` count. The `desiredHealthy` count tells the controller how many pods need to be kept.

Let’s look at how minAvailable is handled.

```go
var minAvailable int
minAvailable, err = intstr.GetScaledValueFromIntOrPercent(pdb.Spec.MinAvailable, int(expectedCount), true)
if err != nil {
  return
}
desiredHealthy = int32(minAvailable)
```

The `desiredHealthy` is set equal to the scaled value of `minAvailable` which makes sense because it is the minimum number of pods that MUST be available.

Now let’s look at how maxUnavailable is handled.

```go
var maxUnavailable int
maxUnavailable, err = intstr.GetScaledValueFromIntOrPercent(pdb.Spec.MaxUnavailable, int(expectedCount), true)
if err != nil {
  return
}
desiredHealthy = expectedCount - int32(maxUnavailable)
```

`desiredHealthy` in this case is calculated by subtracting the scaled value of `maxUnavailable` from the `expectedCount`. The `expectedCount` is simply the value of replica(s) specified in the deployment manifest.

For example, if you have specified 2 replica(s) in the deployment manifest (ie `expectedCount = 2`) and your `maxUnavailable` is set to 1, then:

`desiredHealthy = expectedCount - maxUnavailable = 2 - 1 = 1`.

The controller is allowed to evict 1 pod at most.

The scaled value is computed using the `intstr.GetScaledValueFromIntOrPercent` function.

The `intstr.GetScaledValueFromIntOrPercent` function has the following signature:

```go
intstr.GetScaledValueFromIntOrPercent(value, total, roundUp)
```

**Where:**

- `value` is the user-supplied PDB field (`minAvailable` or `maxUnavailable`), expressed as either an integer or a percentage.
- `total` is the expected number of replicas for the workload.
- `roundUp` controls how fractional results are handled when percentages are used. When `roundUp` is set to true, any fractional result is rounded up to the next integer.

The percentages are always rounded up. Hence, a fraction of a pod is treated as a whole pod.

Consider a deployment with a single replica (`expectedCount = 1`) and a PDB expressed as `50%`.

In both cases, `intstr.GetScaledValueFromIntOrPercent` returns 1.

- With `minAvailable: 50%`, `desiredHealthy` is 1.
  No pods may be disrupted. Eviction is blocked.

- With `maxUnavailable: 50%`, `desiredHealthy` is 1 − 1 = 0.
  Zero healthy pods are required. Eviction is permitted.

The same percentage produces opposite outcomes because it answers two different questions:
**How many must remain versus How many may be taken away.**

## PDB Behavior Tables

The following tables show examples of the relationship between replica counts, the disruption budget and node drain behavior for both `minAvailable` and `maxUnavailable` settings.

### minAvailable Settings

| Replica(s) | minAvailable | allowedDisruptions | Drain behaviour |
|------------|--------------|-------------------|-----------------|
| 1 | 1 | 0 | Drain is blocked. |
| 2 | 1 | 1 | Nodes can be drained one node at a time. |
| 1 | 50% | 0 | same as minAvailable=1 due to rounding up. Drain blocked. |
| 2 | 50% | 1 | Nodes can be drained 1 node at a time |



Now let’s look at how maxUnavailable setting affects drain behaviour

### maxUnavailable Settings

| Replica(s) | maxUnavailable | allowedDisruptions | Drain behaviour |
|------------|----------------|-------------------|-----------------|
| 1 | 1 | 1 | Drain allowed (pod can be evicted) |
| 2 | 1 | 1 | Nodes can be drained 1 node at a time |
| 1 | 50% | 1 | Drain allowed (percentage rounds up) |
| 2 | 50% | 1 | Nodes can be drained 1 node at a time |
Armed with this information, we are now ready to answer the opening question.

The Answer:
Scenario:

You run a stateless service with 2 replicas, each scheduled on a different node.

You’ve configured a PodDisruptionBudget with minAvailable:1

Question 1: How many pods can be evicted simultaneously?

Looking at the table, allowedDisruptions: 1. Hence the answer is 1.  

Follow up: You notice that Kubernetes blocks the drain before evicting the second pod.

Question 2: Why is Kubernetes allowed to block this operation?

Looking at the table, you will notice that allowedDisruptions is 0 when there is a single pod. 

The PodDisruptionBudget is configured to block this voluntary disruption as it violates the budget constraint.

Follow up: You now scale the deployment down to 1 replica.

Question 3: What happens to the drain, and why?

Answer: The drain operation is blocked as it clearly violates the configured disruption budget.

Follow up: you change the PDB to maxUnavailable:50%

Question 4: Does the behavior change? Why or why not?

Answer: Yes, maxUnavailable (because percentages are always rounded up) allows pods to be evicted even if there is a single pod left.

There you go. Next time you encounter PDB’s in an Interview or a production environment, you know how to think about them! 

 
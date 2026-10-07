# Data card

## Evaluation design

A case is a fleet size, a track and a seed. Twelve seeds draw one procedural
circuit each, and each circuit is reused unchanged at fleet sizes of 4, 6, 8 and
10 vehicles, giving 48 cases per method. No seed is drawn twice, so the twelve
circuits are distinct and the 48 cases are twelve tracks crossed with four fleet
sizes rather than 48 independent draws. Within a case every method sees the same
track, initial state and opponent behaviour.

The evaluated vehicle starts last in single file and is the only vehicle under
the method's control; the field is driven by a slow-traffic profile with target
speeds between 11 and 15.8 m/s. Episodes run for at most 2200 steps.

## Endpoints

Overtaking is scored from recorded trajectory in nested tiers: a physical pass
with a sustained lead and no recorded contact, then on-track execution, then
post-pass stability, then a racing rival rather than one already off the surface.
A case passes a tier only if at least one event satisfies every condition in it;
failures and censored records stay in the denominator. Binary rates carry Wilson
95 % intervals and continuous quantities carry normal-approximation intervals.
Three reported columns are not tier rates: rank gain, mean speed and pass time.

## Reporting

Each learned method is the mean over the draws of its training recipe, with the
range those draws span, so no column depends on the choice of a single training
run. The proposed controller is also released with a fused five-member variant;
it is shipped with the code but is not the reported result.

## Boundaries

The simulator represents planar kinematics and contact, not tyre slip, load
transfer or actuator lag. Fleet sizes, the procedural track family and the
opponent profile bound the transfer claims, and nothing in this table is
evidence for real vehicles. The learned comparators were trained under their own
budgets and none is trained to convergence, so the table characterises the
systems as evaluated rather than at equal budgets.

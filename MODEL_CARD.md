# Model card

DNQ-DLC is a hybrid closed-loop controller for multi-vehicle racing. A learned
graph world model and a learned quality proposal act inside a planner that also
carries a rule anchor, handcrafted manoeuvre candidates, speed limits, a weighted
progress/containment/interaction/risk/uncertainty score, and a hard recovery
shield. It is not a fully learned policy, and the shield is a fallback rather
than a formal safety controller.

Intended use is research reproduction in the supplied two-dimensional simulator,
on the fleet sizes and track family of the reported evaluation. It is not
intended for real vehicles or safety-critical deployment.

Reported performance is the mean over five draws of the training recipe, with
the draw range given beside it, because the endpoint counts move more between
draws of one recipe than between some of the controllers compared. The shield is
active on 30 to 46 % of decision steps; removing it leaves the strict tier
unchanged while costing the racing-rival tier and two completions, so the
shielded tier measures the complete controller rather than the learned planner
alone. Prediction error of the imagined ego position is 0.45 to 0.47 m at a
one-step horizon and 0.85 to 1.18 m at four steps. Containment on the evaluated
cases is better than that of every comparator draw, but successful passes of the
proposed controller still spend 15.7 % of the episode on grass.

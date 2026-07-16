# Model card

DNQ-DLC is a hybrid simulator controller combining a learned graph world model and quality proposal with a rule anchor, handcrafted maneuver candidates, speed limits, weighted risk/quality scoring, and hard recovery. It is not a fully learned policy or a formal safety controller.

Intended use is research reproduction in the supplied simulator. It is not intended for real vehicles or safety-critical deployment. Prediction error increases on unseen eight-vehicle track strata, the quality proposal transfers poorly in reported out-of-distribution tests, and successful DNQ-DLC cases have higher grass exposure than Rule Expert in E1.

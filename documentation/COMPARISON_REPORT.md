# Classification Comparison Report

**Agreement rate: 100.0%** (161 of 161 dishes)

Built independently: Partner 1 in Spark SQL (classify_spark.py), Partner 2 in plain pandas (classify_python.py), each computing their own median thresholds from the same source table without seeing the other's code or numbers first.

## Disagreements

None -- the two pipelines agreed on every dish.

## Tricky-case check

- **Party Jollof Rice** (M025) -- should show a LOW/negative margin despite selling a lot -- the classic dish a restaurant thinks is a star but isn't
  - Spark labeled it: **Volume Driver**
  - Python labeled it: **Volume Driver**
  - Both pipelines agree.
- **Point & Kill Croaker Fish** (M082) -- should show HIGH margin despite low sales volume -- easy to overlook on a simple sales-ranked list
  - Spark labeled it: **Hidden Opportunity**
  - Python labeled it: **Hidden Opportunity**
  - Both pipelines agree.
- **Suya Platter** (M083) -- sells well, but a lot of it is thrown away -- margin alone won't catch this, only wastage_percent will
  - Spark labeled it: **Volume Driver**
  - Python labeled it: **Volume Driver**
  - Both pipelines agree.
- **Ofada Rice & Ayamase** (M026) -- customers love it, but it barely makes money -- a favorite that's quietly a drag on profit
  - Spark labeled it: **Volume Driver**
  - Python labeled it: **Volume Driver**
  - Both pipelines agree.
- **Indomie Special** (M124) -- sells well despite a poor rating -- likely propped up by something other than quality (price, habit, lack of alternatives)
  - Spark labeled it: **Volume Driver**
  - Python labeled it: **Volume Driver**
  - Both pipelines agree.
- **Chapman** (M143) -- barely sells at full price -- almost all its volume comes from promotional periods
  - Spark labeled it: **Hidden Opportunity**
  - Python labeled it: **Hidden Opportunity**
  - Both pipelines agree.

# notebooks/

No exploratory Jupyter notebooks were used in this project. All data
processing, modelling and analysis logic lives in versioned, re-runnable
.py scripts under spark_jobs/, spark_sql/, python_pipeline/, and src/ instead
-- a deliberate choice, not an oversight, so that every result in this
project can be reproduced by running a script rather than by re-executing
notebook cells in the right order by hand.

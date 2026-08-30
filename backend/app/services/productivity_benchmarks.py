import math
import re
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProductivityBenchmark


def activity_key(value:str)->str:
    text=re.sub(r"[^a-z0-9]+"," ",str(value or "").lower()).strip()
    stop={"work","works","activity","installation","construction","the","and","for","of"}
    return " ".join(x for x in text.split() if x not in stop)


def _percentile(values:list[float],p:float):
    if not values:return None
    values=sorted(values)
    if len(values)==1:return values[0]
    pos=(len(values)-1)*p
    lo=math.floor(pos);hi=math.ceil(pos)
    if lo==hi:return values[lo]
    return values[lo]+(values[hi]-values[lo])*(pos-lo)


def benchmark_summary(
    db:Session,
    activity_name:str,
    unit:str,
    project_type:str|None=None,
    discipline:str|None=None,
):
    key=activity_key(activity_name)
    rows=db.scalars(select(ProductivityBenchmark).where(
        ProductivityBenchmark.is_active.is_(True),
        ProductivityBenchmark.activity_key==key,
        ProductivityBenchmark.unit==unit,
    )).all()

    exact_project=[x for x in rows if project_type and x.project_type and x.project_type.lower()==project_type.lower()]
    exact_discipline=[x for x in rows if discipline and x.discipline and x.discipline.lower()==discipline.lower()]
    chosen=exact_project or exact_discipline or rows
    scope="Project Type" if exact_project else "Discipline" if exact_discipline else "Company-Wide"

    values=[float(x.rate_per_working_day) for x in chosen if x.rate_per_working_day is not None]
    if not values:
        return {
            "available":False,
            "activity_key":key,
            "unit":unit,
            "sample_count":0,
            "confidence":"None",
            "scope":"No Benchmark",
            "note":"No confirmed benchmark exists yet. The app should show implied schedule productivity only.",
        }

    n=len(values)
    confidence="High" if n>=12 else "Medium" if n>=5 else "Low"
    source_types=sorted({x.source_type for x in chosen})
    return {
        "available":True,
        "activity_key":key,
        "unit":unit,
        "sample_count":n,
        "scope":scope,
        "median_rate":round(median(values),4),
        "p25_rate":round(_percentile(values,.25),4),
        "p75_rate":round(_percentile(values,.75),4),
        "min_rate":round(min(values),4),
        "max_rate":round(max(values),4),
        "confidence":confidence,
        "source_types":source_types,
        "note":"Benchmark range is descriptive company evidence, not an automatic duration instruction.",
    }


def compare_implied_rate(implied_rate:float,benchmark:dict):
    if not benchmark.get("available"):
        return {"status":"No Benchmark","variance_percent":None,"interpretation":"No benchmark judgement applied."}
    median_rate=float(benchmark["median_rate"])
    if median_rate<=0:
        return {"status":"No Benchmark","variance_percent":None,"interpretation":"Benchmark median is not usable."}
    variance=(implied_rate-median_rate)*100/median_rate
    p25=float(benchmark["p25_rate"]);p75=float(benchmark["p75_rate"])
    if implied_rate<p25:
        status="Below Typical Range"
    elif implied_rate>p75:
        status="Above Typical Range"
    else:
        status="Within Typical Range"
    return {
        "status":status,
        "variance_percent":round(variance,1),
        "interpretation":"Compare with project conditions, work fronts, resources and constraints before changing duration.",
    }

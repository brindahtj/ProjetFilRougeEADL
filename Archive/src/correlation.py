from typing import List, Optional
import math

def pearson(x: List[float], y: List[float]) -> Optional[float]:
    if not x or not y or len(x) != len(y):
        return None
    n = len(x)
    mean_x = sum(x)/n
    mean_y = sum(y)/n
    num = sum((xi-mean_x)*(yi-mean_y) for xi, yi in zip(x, y))
    den_x = math.sqrt(sum((xi-mean_x)**2 for xi in x))
    den_y = math.sqrt(sum((yi-mean_y)**2 for yi in y))
    denom = den_x * den_y
    if denom == 0:
        return None
    return num/denom
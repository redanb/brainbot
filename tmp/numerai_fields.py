import os
import sys
from numerapi import NumerAPI

# Initialize NumerAPI
napi = NumerAPI()

# Try to query a model and its submissions with a minimal set of new fields
query = """
{
  models {
    name
    id
    submissions {
      id
      round {
        number
      }
      result {
        corr
        mmc
      }
      status
    }
  }
}
"""

try:
    models = napi.raw_query(query)['data']['models']
    for m in models:
        if m['name'] == 'anant0':
            print(f"Model: {m['name']}")
            for s in m['submissions'][:5]:
                print(s)
except Exception as e:
    print(f"Error: {e}")

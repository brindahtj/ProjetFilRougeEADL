from Archive.Api_ingestion.pipeline import run_pipeline


if __name__ == '__main__':
    run_pipeline(n_cycles=5, interval_sec=60)

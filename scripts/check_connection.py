from databricks.connect import DatabricksSession

def main() -> None:
    spark = DatabricksSession.builder.serverless().getOrCreate()
    for row in spark.range(5).collect():
        print(row.id)
    print("Connection successful!")

if __name__ == "__main__":
    main()
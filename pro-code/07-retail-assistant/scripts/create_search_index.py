"""Plan, then explicitly create a managed-embedding AI Search Delta Sync index."""

from __future__ import annotations

import argparse
import json

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import vectorsearch as v

from scripts.ingest_policies import sql_name


def index_spec(table: str, embedding_model: str) -> v.DeltaSyncVectorIndexSpecRequest:
    """Describe the source and synchronized citation columns."""
    sql_name(table)
    return v.DeltaSyncVectorIndexSpecRequest(
        source_table=table,
        pipeline_type=v.PipelineType.TRIGGERED,
        embedding_source_columns=[
            v.EmbeddingSourceColumn(
                name="content",
                embedding_model_endpoint_name=embedding_model,
            )
        ],
        columns_to_sync=["chunk_id", "content", "source_uri", "title"],
    )


def main() -> None:
    """Preview by default; endpoint/index lifecycle runs only after --apply."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile")
    parser.add_argument("--endpoint", default="northstar-policies")
    parser.add_argument("--index", default="northstar_demo.retail.policy_index")
    parser.add_argument("--table", default="northstar_demo.retail.policy_chunks")
    parser.add_argument("--embedding-model", default="databricks-gte-large-en")
    parser.add_argument(
        "--action", choices=["endpoint", "index", "sync"], default="index"
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    sql_name(args.index)
    spec = index_spec(args.table, args.embedding_model)
    plan = {
        "action": args.action,
        "endpoint": args.endpoint,
        "index": args.index,
        "spec": spec.as_dict(),
    }
    if not args.apply:
        print(json.dumps(plan, indent=2))
        return
    if not args.profile:
        parser.error("--apply requires --profile")
    w = WorkspaceClient(profile=args.profile)
    if args.action == "endpoint":
        created = w.vector_search_endpoints.create_endpoint(
            name=args.endpoint,
            endpoint_type=v.EndpointType.STANDARD,
        )
        print(created.response.as_dict())
        print("Wait for endpoint ONLINE before creating the index.")
    elif args.action == "index":
        print(
            w.vector_search_indexes.create_index(
                name=args.index,
                endpoint_name=args.endpoint,
                primary_key="chunk_id",
                index_type=v.VectorIndexType.DELTA_SYNC,
                delta_sync_index_spec=spec,
            ).as_dict()
        )
        print(
            "Wait for index ready before querying; later source updates require --action sync."
        )
    else:
        w.vector_search_indexes.sync_index(index_name=args.index)
        print("Sync submitted; check index status before querying.")


if __name__ == "__main__":
    main()

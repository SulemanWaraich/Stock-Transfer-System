import pandas as pd, numpy as np

def compute_velocity(sales: pd.DataFrame, lookback_days=7) -> pd.DataFrame:
    if sales.empty:
        return pd.DataFrame(columns=["store_id","store_name","sku","style","size","avg_daily_sales"])
    sales = sales.copy()
    sales["date"] = pd.to_datetime(sales["date"])
    max_date = sales["date"].max()
    start_date = max_date - pd.Timedelta(days=lookback_days - 1)
    window = sales[(sales["date"] >= start_date) & (sales["date"] <= max_date)]
    days = lookback_days
    agg = window.groupby(["store_id","store_name","sku","style","size"], dropna=False)["units_sold"].sum().reset_index()
    agg["avg_daily_sales"] = agg["units_sold"] / days
    return agg[["store_id","store_name","sku","style","size","avg_daily_sales"]]

def plan_transfers(stock: pd.DataFrame, velocity: pd.DataFrame, stores: pd.DataFrame, rules: dict):
    df = (stock.merge(velocity, on=["store_id","store_name","sku","style","size"], how="left")
               .merge(stores, on=["store_id","store_name"], how="left"))
    df["avg_daily_sales"] = df["avg_daily_sales"].fillna(0.0)
    target_days = int(rules.get("target_days_cover", 7))
    min_display = int(rules.get("min_display", 1))
    pack_size = int(rules.get("pack_size", 1))

    df["target"] = np.maximum(min_display, np.ceil(df["avg_daily_sales"] * target_days)).astype(int)
    df["surplus"] = (df["on_hand"] - df["target"]).clip(lower=0)
    df["shortage"] = (df["target"] - df["on_hand"]).clip(lower=0)

    transfers = []
    key_cols = ["sku","style","size"]
    for key, group in df.groupby(key_cols):
        sources = group[group["surplus"] > 0].copy().sort_values(by=["surplus"], ascending=False)
        sinks = group[group["shortage"] > 0].copy().sort_values(by=["priority","shortage"], ascending=[False, False])
        if sources.empty or sinks.empty:
            continue
        for _, sink_row in sinks.iterrows():
            need = int(sink_row["shortage"]); 
            for sidx, src_row in sources.iterrows():
                if need <= 0: break
                available = int(src_row["surplus"])
                if available <= 0: continue
                ship_qty = min(available, need)
                if pack_size > 1:
                    ship_qty = (ship_qty // pack_size) * pack_size
                    if ship_qty == 0: continue
                transfers.append({
                    "from_store_id": src_row["store_id"],
                    "from_store": src_row["store_name"],
                    "to_store_id": sink_row["store_id"],
                    "to_store": sink_row["store_name"],
                    "sku": key[0], "style": key[1], "size": key[2],
                    "qty": int(ship_qty)
                })
                sources.loc[sidx, "surplus"] -= ship_qty
                need -= ship_qty

    plan_df = pd.DataFrame(transfers)
    if plan_df.empty:
        plan_df = pd.DataFrame(columns=["from_store_id","from_store","to_store_id","to_store","sku","style","size","qty"])
    pick = plan_df.groupby(["from_store_id","from_store","sku","style","size"], as_index=False)["qty"].sum()
    recv = plan_df.groupby(["to_store_id","to_store","sku","style","size"], as_index=False)["qty"].sum()

    df["days_cover_before"] = df.apply(lambda r: r["on_hand"] / (r["avg_daily_sales"] if r["avg_daily_sales"]>0 else 0.0001), axis=1)
    after = stock.copy()
    for _, t in plan_df.iterrows():
        msrc = ((after["store_id"]==t["from_store_id"]) & (after["store_name"]==t["from_store"]) &
                (after["sku"]==t["sku"]) & (after["style"]==t["style"]) & (after["size"]==t["size"]))
        after.loc[msrc, "on_hand"] = after.loc[msrc, "on_hand"] - t["qty"]
        mdst = ((after["store_id"]==t["to_store_id"]) & (after["store_name"]==t["to_store"]) &
                (after["sku"]==t["sku"]) & (after["style"]==t["style"]) & (after["size"]==t["size"]))
        if mdst.any():
            after.loc[mdst, "on_hand"] = after.loc[mdst, "on_hand"] + t["qty"]
        else:
            newrow = {"store_id":t["to_store_id"],"store_name":t["to_store"],
                      "sku":t["sku"],"style":t["style"],"size":t["size"],"on_hand":t["qty"]}
            after = pd.concat([after, pd.DataFrame([newrow])], ignore_index=True)

    kpi = (after.merge(df[["store_id","store_name","sku","style","size","avg_daily_sales","days_cover_before"]],
                       on=["store_id","store_name","sku","style","size"], how="left"))
    kpi["days_cover_after"] = kpi.apply(lambda r: r["on_hand"] / (r["avg_daily_sales"] if r["avg_daily_sales"]>0 else 0.0001), axis=1)
    kpi = kpi.rename(columns={"on_hand":"on_hand_after"})
    kpi = kpi.merge(stock.rename(columns={"on_hand":"on_hand_before"}),
                    on=["store_id","store_name","sku","style","size"], how="left")
    return plan_df, pick, recv, kpi

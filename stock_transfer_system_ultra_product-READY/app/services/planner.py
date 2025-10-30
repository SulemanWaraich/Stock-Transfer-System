import pandas as pd, numpy as np

def compute_velocity(sales: pd.DataFrame, lookback_days=7) -> pd.DataFrame:
    """
    FORMULA 1: Average Daily Sales Velocity
    ========================================
    avg_daily_sales = total_units_sold / lookback_days
    
    This calculates how many units sell per day on average for each store/SKU/size combination.
    Example: If 21 units sold in 7 days → velocity = 21/7 = 3 units/day
    """
    if sales.empty:
        return pd.DataFrame(columns=["store_id","store_name","sku","style","size","avg_daily_sales"])
    
    sales = sales.copy()
    sales["date"] = pd.to_datetime(sales["date"])
    max_date = sales["date"].max()
    start_date = max_date - pd.Timedelta(days=lookback_days - 1)
    
    # Filter to lookback window
    window = sales[(sales["date"] >= start_date) & (sales["date"] <= max_date)]
    days = lookback_days
    
    # Aggregate total units sold per store/SKU/size
    agg = window.groupby(["store_id","store_name","sku","style","size"], dropna=False)["units_sold"].sum().reset_index()
    
    # FORMULA: Average daily sales = total sold / number of days
    agg["avg_daily_sales"] = agg["units_sold"] / days
    
    return agg[["store_id","store_name","sku","style","size","avg_daily_sales"]]


def plan_transfers(stock: pd.DataFrame, velocity: pd.DataFrame, stores: pd.DataFrame, rules: dict):
    """
    FORMULAS 2-5: Stock Transfer Planning Logic
    ============================================
    
    FORMULA 2: Target Stock Level
    target = max(min_display, ceil(avg_daily_sales × target_days_cover))
    
    This ensures each store has enough inventory to cover target days of sales.
    Example: If velocity = 3 units/day, target_days = 7 → target = ceil(3×7) = 21 units
    
    FORMULA 3: Surplus Calculation
    surplus = max(0, on_hand - target)
    
    How many units above target (can be sent to other stores).
    Example: on_hand=30, target=21 → surplus = 9 units
    
    FORMULA 4: Shortage Calculation  
    shortage = max(0, target - on_hand)
    
    How many units below target (needs to receive from other stores).
    Example: on_hand=10, target=21 → shortage = 11 units
    
    FORMULA 5: Days of Cover
    days_cover = on_hand / avg_daily_sales
    
    How many days the current inventory will last at current sales rate.
    Example: on_hand=21, velocity=3/day → days_cover = 7 days
    """
    
    # Merge stock with velocity and store priority
    df = (stock.merge(velocity, on=["store_id","store_name","sku","style","size"], how="left")
               .merge(stores, on=["store_id","store_name"], how="left"))
    df["avg_daily_sales"] = df["avg_daily_sales"].fillna(0.0)
    
    # Extract rules
    target_days = int(rules.get("target_days_cover", 7))
    min_display = int(rules.get("min_display", 1))
    pack_size = int(rules.get("pack_size", 1))

    # FORMULA 2: Calculate target stock level
    # Target = max(minimum display, ceiling of (velocity × target days))
    df["target"] = np.maximum(min_display, np.ceil(df["avg_daily_sales"] * target_days)).astype(int)
    
    # FORMULA 3: Calculate surplus (how much extra above target)
    # Surplus = max(0, current stock - target)
    df["surplus"] = (df["on_hand"] - df["target"]).clip(lower=0)
    
    # FORMULA 4: Calculate shortage (how much needed to reach target)
    # Shortage = max(0, target - current stock)
    df["shortage"] = (df["target"] - df["on_hand"]).clip(lower=0)

    # Transfer matching algorithm: move surplus to shortage stores
    transfers = []
    key_cols = ["sku","style","size"]
    
    for key, group in df.groupby(key_cols):
        # Sources = stores with surplus (sorted by surplus amount, descending)
        sources = group[group["surplus"] > 0].copy().sort_values(by=["surplus"], ascending=False)
        
        # Sinks = stores with shortage (sorted by priority then shortage, both descending)
        sinks = group[group["shortage"] > 0].copy().sort_values(by=["priority","shortage"], ascending=[False, False])
        
        if sources.empty or sinks.empty:
            continue
            
        # Match surplus stores to shortage stores
        for _, sink_row in sinks.iterrows():
            need = int(sink_row["shortage"])
            
            for sidx, src_row in sources.iterrows():
                if need <= 0: 
                    break
                    
                available = int(src_row["surplus"])
                if available <= 0: 
                    continue
                
                # Transfer the minimum of (what's needed, what's available)
                ship_qty = min(available, need)
                
                # Adjust to pack size (can only ship in multiples of pack_size)
                if pack_size > 1:
                    ship_qty = (ship_qty // pack_size) * pack_size
                    if ship_qty == 0: 
                        continue
                
                # Record the transfer
                transfers.append({
                    "from_store_id": src_row["store_id"],
                    "from_store": src_row["store_name"],
                    "to_store_id": sink_row["store_id"],
                    "to_store": sink_row["store_name"],
                    "sku": key[0], 
                    "style": key[1], 
                    "size": key[2],
                    "qty": int(ship_qty)
                })
                
                # Update remaining surplus and shortage
                sources.loc[sidx, "surplus"] -= ship_qty
                need -= ship_qty

    # Create transfer plan dataframe
    plan_df = pd.DataFrame(transfers)
    if plan_df.empty:
        plan_df = pd.DataFrame(columns=["from_store_id","from_store","to_store_id","to_store","sku","style","size","qty"])
    
    # Generate pick list (what to pick from each source store)
    pick = plan_df.groupby(["from_store_id","from_store","sku","style","size"], as_index=False)["qty"].sum()
    
    # Generate receive list (what each destination store will receive)
    recv = plan_df.groupby(["to_store_id","to_store","sku","style","size"], as_index=False)["qty"].sum()

    # FORMULA 5: Calculate days of cover BEFORE transfers
    # Days cover = current inventory / daily sales rate
    df["days_cover_before"] = df.apply(
        lambda r: r["on_hand"] / (r["avg_daily_sales"] if r["avg_daily_sales"] > 0 else 0.0001), 
        axis=1
    )
    
    # Simulate inventory AFTER transfers
    after = stock.copy()
    for _, t in plan_df.iterrows():
        # Deduct from source store
        msrc = ((after["store_id"]==t["from_store_id"]) & (after["store_name"]==t["from_store"]) &
                (after["sku"]==t["sku"]) & (after["style"]==t["style"]) & (after["size"]==t["size"]))
        after.loc[msrc, "on_hand"] = after.loc[msrc, "on_hand"] - t["qty"]
        
        # Add to destination store
        mdst = ((after["store_id"]==t["to_store_id"]) & (after["store_name"]==t["to_store"]) &
                (after["sku"]==t["sku"]) & (after["style"]==t["style"]) & (after["size"]==t["size"]))
        if mdst.any():
            after.loc[mdst, "on_hand"] = after.loc[mdst, "on_hand"] + t["qty"]
        else:
            # Create new row if destination store didn't have this SKU before
            newrow = {
                "store_id": t["to_store_id"],
                "store_name": t["to_store"],
                "sku": t["sku"],
                "style": t["style"],
                "size": t["size"],
                "on_hand": t["qty"]
            }
            after = pd.concat([after, pd.DataFrame([newrow])], ignore_index=True)

    # Calculate KPIs with before/after comparison
    kpi = (after.merge(
        df[["store_id","store_name","sku","style","size","avg_daily_sales","days_cover_before"]],
        on=["store_id","store_name","sku","style","size"], 
        how="left"
    ))
    
    # FORMULA 5 (again): Calculate days of cover AFTER transfers
    kpi["days_cover_after"] = kpi.apply(
        lambda r: r["on_hand"] / (r["avg_daily_sales"] if r["avg_daily_sales"] > 0 else 0.0001), 
        axis=1
    )
    
    kpi = kpi.rename(columns={"on_hand": "on_hand_after"})
    kpi = kpi.merge(
        stock.rename(columns={"on_hand": "on_hand_before"}),
        on=["store_id","store_name","sku","style","size"], 
        how="left"
    )
    
    return plan_df, pick, recv, kpi
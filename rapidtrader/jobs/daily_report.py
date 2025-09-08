"""Daily Detailed Report Generator for RapidTrader.

Generates comprehensive daily trading reports with detailed decision analysis,
signal breakdowns, filtering reasons, and risk management decisions.
Reports are saved to files with timestamps for historical tracking.
"""

import os
import json
from datetime import date, datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from sqlalchemy import text
from ..core.db import get_engine
from ..core.config import settings


@dataclass
class SignalDetail:
    """Individual signal details for a symbol."""
    symbol: str
    sector: str
    rsi_signal: str
    sma_signal: str
    final_signal: str
    strategy_used: str
    current_price: float
    atr_14: Optional[float] = None
    position_qty: int = 0
    
    
@dataclass
class OrderDetail:
    """Individual order details."""
    symbol: str
    side: str
    quantity: int
    reason: str
    price: Optional[float] = None
    sector: Optional[str] = None
    

@dataclass
class FilteringDetail:
    """Details about why symbols were filtered out."""
    symbol: str
    reason: str
    details: Optional[str] = None


@dataclass
class MarketState:
    """Market state information."""
    date: date
    spy_close: Optional[float]
    spy_sma200: Optional[float]
    bull_gate: bool
    kill_switch_active: bool
    kill_switch_reason: Optional[str]
    pct_entries_filtered: float
    total_candidates: int
    filtered_candidates: int


@dataclass
class DailyReport:
    """Complete daily trading report."""
    report_date: date
    generation_time: datetime
    market_state: MarketState
    signals: List[SignalDetail]
    orders: List[OrderDetail]
    filtered_symbols: List[FilteringDetail]
    summary_stats: Dict[str, Any]


def get_market_state_details(trade_date: date) -> MarketState:
    """Get detailed market state information.
    
    Args:
        trade_date: Trading date to analyze
        
    Returns:
        MarketState object with detailed information
    """
    eng = get_engine()
    
    with eng.begin() as conn:
        # Get market state
        market_data = conn.execute(text("""
            SELECT spy_close, spy_sma200, bull_gate, 
                   pct_entries_filtered, total_candidates, filtered_candidates
            FROM market_state 
            WHERE d = :d
        """), {"d": trade_date}).first()
        
        # Check kill switch status (handle missing table gracefully)
        kill_data = None
        try:
            kill_data = conn.execute(text("""
                SELECT is_active, reason 
                FROM kill_switch_log 
                WHERE d = :d 
                ORDER BY created_at DESC 
                LIMIT 1
            """), {"d": trade_date}).first()
        except Exception:
            # kill_switch_log table may not exist yet
            pass
    
    if market_data:
        spy_close, spy_sma200, bull_gate, pct_filtered, total, filtered = market_data
    else:
        spy_close = spy_sma200 = None
        bull_gate = True
        pct_filtered = total = filtered = 0
    
    kill_active = False
    kill_reason = None
    if kill_data:
        kill_active, kill_reason = kill_data
    
    return MarketState(
        date=trade_date,
        spy_close=spy_close,
        spy_sma200=spy_sma200,
        bull_gate=bool(bull_gate),
        kill_switch_active=bool(kill_active),
        kill_switch_reason=kill_reason,
        pct_entries_filtered=float(pct_filtered or 0),
        total_candidates=int(total or 0),
        filtered_candidates=int(filtered or 0)
    )


def get_signal_details(trade_date: date) -> List[SignalDetail]:
    """Get detailed signal information for all symbols.
    
    Args:
        trade_date: Trading date to analyze
        
    Returns:
        List of SignalDetail objects
    """
    eng = get_engine()
    
    with eng.begin() as conn:
        # Get all signals with symbol and sector info
        signal_data = conn.execute(text("""
            SELECT s.symbol, sym.sector,
                   MAX(CASE WHEN s.strategy = 'RSI_MR' THEN s.direction END) as rsi_signal,
                   MAX(CASE WHEN s.strategy = 'SMA_X' THEN s.direction END) as sma_signal,
                   b.close as current_price,
                   COALESCE(p.qty, 0) as position_qty
            FROM signals_daily s
            JOIN symbols sym ON s.symbol = sym.symbol
            LEFT JOIN bars_daily b ON s.symbol = b.symbol AND s.d = b.d
            LEFT JOIN positions p ON s.symbol = p.symbol
            WHERE s.d = :d
            GROUP BY s.symbol, sym.sector, b.close, p.qty
            ORDER BY s.symbol
        """), {"d": trade_date}).all()
    
    signals = []
    for row in signal_data:
        symbol, sector, rsi_signal, sma_signal, current_price, position_qty = row
        
        # Determine final signal (same logic as eod_trade.py)
        final_signal = "hold"
        strategy_used = "none"
        
        if rsi_signal == "sell" or sma_signal == "sell":
            final_signal = "sell"
            strategy_used = "RSI_MR" if rsi_signal == "sell" else "SMA_X"
        elif rsi_signal == "buy" or sma_signal == "buy":
            final_signal = "buy"
            strategy_used = "RSI_MR" if rsi_signal == "buy" else "SMA_X"
        
        signals.append(SignalDetail(
            symbol=symbol,
            sector=sector or "Unknown",
            rsi_signal=rsi_signal or "hold",
            sma_signal=sma_signal or "hold",
            final_signal=final_signal,
            strategy_used=strategy_used,
            current_price=float(current_price or 0),
            position_qty=int(position_qty or 0)
        ))
    
    return signals


def get_order_details(trade_date: date) -> List[OrderDetail]:
    """Get detailed order information.
    
    Args:
        trade_date: Trading date to analyze
        
    Returns:
        List of OrderDetail objects
    """
    eng = get_engine()
    
    with eng.begin() as conn:
        order_data = conn.execute(text("""
            SELECT o.symbol, o.side, o.qty, o.reason,
                   b.close as price, sym.sector
            FROM orders_eod o
            LEFT JOIN bars_daily b ON o.symbol = b.symbol AND o.d = b.d
            LEFT JOIN symbols sym ON o.symbol = sym.symbol
            WHERE o.d = :d
            ORDER BY o.side, o.symbol
        """), {"d": trade_date}).all()
    
    orders = []
    for symbol, side, qty, reason, price, sector in order_data:
        orders.append(OrderDetail(
            symbol=symbol,
            side=side,
            quantity=int(qty or 0),
            reason=reason or "unknown",
            price=float(price or 0),
            sector=sector or "Unknown"
        ))
    
    return orders


def analyze_filtering_reasons(trade_date: date, signals: List[SignalDetail], orders: List[OrderDetail]) -> List[FilteringDetail]:
    """Analyze why symbols were filtered out of trading decisions.
    
    Args:
        trade_date: Trading date to analyze
        signals: List of signal details
        orders: List of order details
        
    Returns:
        List of FilteringDetail objects
    """
    filtered = []
    
    # Create lookup sets for efficiency
    order_symbols = {order.symbol for order in orders if order.quantity > 0}
    blocked_buy_symbols = {order.symbol for order in orders if order.side == "buy" and order.quantity == 0}
    
    # Analyze signals that didn't result in orders
    for signal in signals:
        if signal.final_signal == "hold":
            continue  # Hold signals are not filtered, they're intentional
        
        if signal.symbol not in order_symbols:
            if signal.symbol in blocked_buy_symbols:
                filtered.append(FilteringDetail(
                    symbol=signal.symbol,
                    reason="market_gate_block",
                    details=f"Buy signal blocked by bear market filter ({signal.strategy_used})"
                ))
            elif signal.final_signal == "buy":
                # Buy signal but no order - could be various reasons
                filtered.append(FilteringDetail(
                    symbol=signal.symbol,
                    reason="entry_filtered",
                    details=f"Buy signal filtered - possible reasons: sector limits, position sizing, kill switch ({signal.strategy_used})"
                ))
            elif signal.final_signal == "sell" and signal.position_qty == 0:
                # Sell signal but no position to sell
                filtered.append(FilteringDetail(
                    symbol=signal.symbol,
                    reason="no_position_to_sell",
                    details=f"Sell signal but no current position ({signal.strategy_used})"
                ))
    
    return filtered


def calculate_summary_stats(market_state: MarketState, signals: List[SignalDetail], 
                          orders: List[OrderDetail], filtered: List[FilteringDetail]) -> Dict[str, Any]:
    """Calculate summary statistics for the report.
    
    Args:
        market_state: Market state information
        signals: List of signal details
        orders: List of order details
        filtered: List of filtered symbols
        
    Returns:
        Dictionary of summary statistics
    """
    # Signal counts
    signal_counts = {"buy": 0, "sell": 0, "hold": 0}
    strategy_counts = {"RSI_MR": 0, "SMA_X": 0, "both": 0}
    
    for signal in signals:
        signal_counts[signal.final_signal] += 1
        
        if signal.rsi_signal != "hold" and signal.sma_signal != "hold":
            strategy_counts["both"] += 1
        elif signal.rsi_signal != "hold":
            strategy_counts["RSI_MR"] += 1
        elif signal.sma_signal != "hold":
            strategy_counts["SMA_X"] += 1
    
    # Order counts and values
    order_counts = {"buy": 0, "sell": 0}
    order_values = {"buy": 0.0, "sell": 0.0}
    blocked_orders = 0
    
    for order in orders:
        if order.quantity == 0 and order.side == "buy":
            blocked_orders += 1
        else:
            order_counts[order.side] += 1
            if order.price and order.quantity > 0:
                order_values[order.side] += order.price * order.quantity
    
    # Filtering analysis
    filtering_reasons = {}
    for f in filtered:
        filtering_reasons[f.reason] = filtering_reasons.get(f.reason, 0) + 1
    
    return {
        "total_symbols_analyzed": len(signals),
        "signal_counts": signal_counts,
        "strategy_signal_counts": strategy_counts,
        "order_counts": order_counts,
        "order_values": order_values,
        "blocked_buy_orders": blocked_orders,
        "filtering_reasons": filtering_reasons,
        "market_regime": "BULL" if market_state.bull_gate else "BEAR",
        "kill_switch_status": "ACTIVE" if market_state.kill_switch_active else "INACTIVE"
    }


def generate_daily_report(trade_date: date) -> DailyReport:
    """Generate a comprehensive daily trading report.
    
    Args:
        trade_date: Trading date to generate report for
        
    Returns:
        Complete DailyReport object
    """
    print(f"INFO: Generating detailed report for {trade_date}")
    
    # Gather all report data
    market_state = get_market_state_details(trade_date)
    signals = get_signal_details(trade_date)
    orders = get_order_details(trade_date)
    filtered = analyze_filtering_reasons(trade_date, signals, orders)
    summary_stats = calculate_summary_stats(market_state, signals, orders, filtered)
    
    return DailyReport(
        report_date=trade_date,
        generation_time=datetime.now(),
        market_state=market_state,
        signals=signals,
        orders=orders,
        filtered_symbols=filtered,
        summary_stats=summary_stats
    )


def save_report_to_file(report: DailyReport, output_dir: str = "reports") -> str:
    """Save the daily report to a file.
    
    Args:
        report: DailyReport object to save
        output_dir: Directory to save reports in
        
    Returns:
        Path to the saved report file
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = report.generation_time.strftime("%Y%m%d_%H%M%S")
    filename = f"daily_report_{report.report_date}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    # Convert report to dictionary for JSON serialization
    report_dict = asdict(report)
    
    # Convert date objects to strings for JSON
    report_dict["report_date"] = report.report_date.isoformat()
    report_dict["generation_time"] = report.generation_time.isoformat()
    report_dict["market_state"]["date"] = report.market_state.date.isoformat()
    
    # Save to JSON file
    with open(filepath, 'w') as f:
        json.dump(report_dict, f, indent=2, default=str)
    
    print(f"SUCCESS: Detailed report saved to {filepath}")
    return filepath


def save_human_readable_report(report: DailyReport, output_dir: str = "reports") -> str:
    """Save a human-readable version of the report.
    
    Args:
        report: DailyReport object to save
        output_dir: Directory to save reports in
        
    Returns:
        Path to the saved human-readable report file
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename
    timestamp = report.generation_time.strftime("%Y%m%d_%H%M%S")
    filename = f"daily_report_{report.report_date}_{timestamp}.txt"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write(f"RAPIDTRADER DAILY TRADING REPORT\n")
        f.write(f"Report Date: {report.report_date}\n")
        f.write(f"Generated: {report.generation_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        # Market State Section
        f.write("MARKET STATE ANALYSIS\n")
        f.write("-" * 40 + "\n")
        ms = report.market_state
        f.write(f"Market Regime: {'BULL' if ms.bull_gate else 'BEAR'} Market\n")
        if ms.spy_close and ms.spy_sma200:
            f.write(f"SPY Close: ${ms.spy_close:.2f}\n")
            f.write(f"SPY 200-SMA: ${ms.spy_sma200:.2f}\n")
            f.write(f"SPY vs SMA: {'Above' if ms.spy_close >= ms.spy_sma200 else 'Below'} ({ms.spy_close/ms.spy_sma200*100-100:+.1f}%)\n")
        
        f.write(f"Kill Switch: {'ACTIVE' if ms.kill_switch_active else 'INACTIVE'}\n")
        if ms.kill_switch_reason:
            f.write(f"Kill Switch Reason: {ms.kill_switch_reason}\n")
        
        f.write(f"Total Candidates: {ms.total_candidates}\n")
        f.write(f"Filtered Out: {ms.filtered_candidates} ({ms.pct_entries_filtered:.1f}%)\n\n")
        
        # Summary Statistics
        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 40 + "\n")
        stats = report.summary_stats
        f.write(f"Symbols Analyzed: {stats['total_symbols_analyzed']}\n")
        f.write(f"Signals Generated:\n")
        for signal_type, count in stats['signal_counts'].items():
            f.write(f"  {signal_type.upper()}: {count}\n")
        
        f.write(f"Orders Created:\n")
        for side, count in stats['order_counts'].items():
            value = stats['order_values'][side]
            f.write(f"  {side.upper()}: {count} orders (${value:,.2f})\n")
        
        if stats['blocked_buy_orders'] > 0:
            f.write(f"  BLOCKED BUYS: {stats['blocked_buy_orders']} orders\n")
        
        f.write("\n")
        
        # Filtering Analysis
        if report.filtered_symbols:
            f.write("FILTERING ANALYSIS\n")
            f.write("-" * 40 + "\n")
            for reason, count in stats['filtering_reasons'].items():
                f.write(f"{reason.replace('_', ' ').title()}: {count} symbols\n")
            f.write("\n")
        
        # Detailed Signal Analysis
        f.write("DETAILED SIGNAL ANALYSIS\n")
        f.write("-" * 40 + "\n")
        
        # Group signals by final decision
        buy_signals = [s for s in report.signals if s.final_signal == "buy"]
        sell_signals = [s for s in report.signals if s.final_signal == "sell"]
        
        if buy_signals:
            f.write(f"BUY SIGNALS ({len(buy_signals)}):\n")
            for signal in sorted(buy_signals, key=lambda x: x.symbol):
                f.write(f"  {signal.symbol:6} | ${signal.current_price:7.2f} | {signal.strategy_used:6} | Sector: {signal.sector:15} | RSI: {signal.rsi_signal:4} | SMA: {signal.sma_signal:4}\n")
            f.write("\n")
        
        if sell_signals:
            f.write(f"SELL SIGNALS ({len(sell_signals)}):\n")
            for signal in sorted(sell_signals, key=lambda x: x.symbol):
                pos_info = f"(Pos: {signal.position_qty})" if signal.position_qty > 0 else "(No Pos)"
                f.write(f"  {signal.symbol:6} | ${signal.current_price:7.2f} | {signal.strategy_used:6} | Sector: {signal.sector:15} | {pos_info:10} | RSI: {signal.rsi_signal:4} | SMA: {signal.sma_signal:4}\n")
            f.write("\n")
        
        # Orders Created
        if report.orders:
            f.write("ORDERS CREATED\n")
            f.write("-" * 40 + "\n")
            
            buy_orders = [o for o in report.orders if o.side == "buy" and o.quantity > 0]
            sell_orders = [o for o in report.orders if o.side == "sell"]
            blocked_orders = [o for o in report.orders if o.side == "buy" and o.quantity == 0]
            
            if buy_orders:
                f.write(f"BUY ORDERS ({len(buy_orders)}):\n")
                for order in sorted(buy_orders, key=lambda x: x.symbol):
                    value = order.quantity * (order.price or 0)
                    f.write(f"  {order.symbol:6} | {order.quantity:4} shares | ${value:8,.2f} | {order.reason}\n")
                f.write("\n")
            
            if sell_orders:
                f.write(f"SELL ORDERS ({len(sell_orders)}):\n")
                for order in sorted(sell_orders, key=lambda x: x.symbol):
                    f.write(f"  {order.symbol:6} | {'Full Exit' if order.quantity == 0 else f'{order.quantity} shares':12} | {order.reason}\n")
                f.write("\n")
            
            if blocked_orders:
                f.write(f"BLOCKED BUY ORDERS ({len(blocked_orders)}):\n")
                for order in sorted(blocked_orders, key=lambda x: x.symbol):
                    f.write(f"  {order.symbol:6} | Market Gate Block | {order.reason}\n")
                f.write("\n")
        
        # Filtered Symbols Detail
        if report.filtered_symbols:
            f.write("FILTERED SYMBOLS DETAIL\n")
            f.write("-" * 40 + "\n")
            for filtered in sorted(report.filtered_symbols, key=lambda x: x.symbol):
                f.write(f"  {filtered.symbol:6} | {filtered.reason:20} | {filtered.details or 'N/A'}\n")
            f.write("\n")
        
        f.write("=" * 80 + "\n")
        f.write("End of Report\n")
    
    print(f"SUCCESS: Human-readable report saved to {filepath}")
    return filepath


def generate_and_save_daily_report(trade_date: date, output_dir: str = "reports") -> Tuple[str, str]:
    """Generate and save both JSON and human-readable daily reports.
    
    Args:
        trade_date: Trading date to generate report for
        output_dir: Directory to save reports in
        
    Returns:
        Tuple of (json_filepath, text_filepath)
    """
    print(f"INFO: Starting detailed report generation for {trade_date}")
    
    # Generate the report
    report = generate_daily_report(trade_date)
    
    # Save both formats
    json_path = save_report_to_file(report, output_dir)
    text_path = save_human_readable_report(report, output_dir)
    
    print(f"SUCCESS: Detailed reports generated successfully")
    print(f"  JSON: {json_path}")
    print(f"  Text: {text_path}")
    
    return json_path, text_path

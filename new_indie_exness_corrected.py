# indie:lang_version = 5

from math import nan, isnan

from indie import (
    indicator,
    param,
    plot,
    color,
    MainContext,
    MutSeriesF,
    sec_context,
    TimeFrame,
    line_style
)

from indie.algorithms import Ema, Rsi, Atr, Adx
from indie.drawings import (
    LabelRel,
    LabelAbs,
    AbsolutePosition,
    RelativePosition,
    vertical_anchor as va,
    horizontal_anchor as ha
)


# Adaptive hybrid trailing is a visual/backtest stop manager for M1 charts.

# Option A uses two legs: Early 60% at confirmation close, Midpoint 40% at (high + low) / 2.
# Common SL/TP and adaptive trailing are anchored to midpoint. This is chart-side simulation only.

# ============================================================
# HIGHER TIMEFRAME CONFIRMATION
# ============================================================

@sec_context
def ConfirmHtfEma(self):
    ema20 = Ema.new(self.close, 20)
    ema50 = Ema.new(self.close, 50)
    return ema20[1], ema50[1]


@sec_context
def ConfirmCandle(self):
    average_volume = (
        self.volume[2] + self.volume[3] + self.volume[4]
        + self.volume[5] + self.volume[6] + self.volume[7]
        + self.volume[8] + self.volume[9] + self.volume[10]
        + self.volume[11]
    ) / 10.0

    return (
        self.open[1],
        self.close[1],
        self.volume[1],
        average_volume
    )


# ============================================================
# INDICATOR SETTINGS
# ============================================================

@indicator(
    'KS Trader Desk - XAUUSD OB FVG Scalper',
    overlay_main_pane=True
)

@param.str(
    'risk_reward',
    default='1:2',
    options=['1:1', '1:1.5', '1:2', '1:3', '1:4'],
    title='Risk Reward Ratio'
)

@param.float(
    'account_capital',
    default=200.0,
    min=1.0,
    title='Actual Account Capital / Balance (USD)'
)

@param.float(
    'risk_percent',
    default=5.0,
    min=5.0,
    max=5.0,
    title='Normal Risk Target (%)'
)

@param.float(
    'risk_buffer_percent',
    default=2.0,
    min=0.0,
    max=2.0,
    title='Additional Risk Buffer (%)'
)

@param.float(
    'contract_size',
    default=100.0,
    min=1.0,
    title='Contract Size (XAU oz per 1.00 lot)'
)

@param.bool(
    'adaptive_trailing_enabled',
    default=True,
    title='Enable Adaptive Hybrid Trailing (M1 chart only)'
)

@param.float(
    'break_even_buffer',
    default=0.0,
    min=0.0,
    title='Break-even Cost Buffer (price units; 0 = entry)'
)

@param.str(
    'delete_setup',
    default='None',
    options=[
        'None',
        'Primary BUY',
        'Primary SELL',
        'Second BUY',
        'Second SELL',
        'Third BUY',
        'Third SELL',
        'Fourth BUY',
        'Fourth SELL',
        'Fifth BUY',
        'Fifth SELL'
    ],
    title='Hide One Setup'
)

@param.int(
    'delete_bar_index',
    default=-1,
    min=-1,
    title='Setup Bar Index (-1 = Disabled)'
)

@param.int(
    'manual_exit_bar_index',
    default=-1,
    min=-1,
    title='Manual Exit Bar Index (-1 = Disabled)'
)

@param.bool(
    'show_bar_index',
    default=True,
    title='Show Current Bar Number'
)

@param.bool(
    'show_entry_descriptions',
    default=True,
    title='Show Entry Descriptions'
)

@param.bool(
    'show_daily_report',
    default=True,
    title='Show Daily + Monthly P/L Report'
)

@param.bool(
    'show_monthly_daily_breakdown',
    default=True,
    title='Show Each Day Net P/L In Monthly Report'
)

@param.int(
    'report_date',
    default=20261118,
    min=19700101,
    max=21001231,
    title='Custom P/L Report Date (YYYYMMDD, IST)'
)

@plot.line(id='ema9', color=color.GREEN, title='EMA 9')
@plot.line(id='ema20', color=color.RED, title='EMA 20')
@plot.line(id='ema50', color=color.BLUE, title='EMA 50')
@plot.line(id='ema200', color=color.YELLOW, title='EMA 200')

@plot.line(id='entry', color=color.MAROON, title='Entry 1 Price')
@plot.line(id='second_entry_price', color=color.BLACK, line_style=line_style.DOTTED, line_width=4, title='Entry 2 Price')
@plot.line(id='third_entry_price', color=color.FUCHSIA, line_style=line_style.DOTTED, line_width=4, title='Entry 3 Price')
@plot.line(id='fourth_entry_price', color=color.YELLOW, line_style=line_style.DOTTED, line_width=4, title='Entry 4 Price')
@plot.line(id='fifth_entry_price', color=color.PURPLE, line_style=line_style.DOTTED, line_width=4, title='Entry 5 Price')

@plot.line(id='sl', color=color.RED, line_width=3, title='Adaptive Stop Loss (visual simulation)')
@plot.line(id='tp', color=color.GREEN, line_width=3, title='Take Profit')

@plot.fill(
    'sl', 'entry',
    color=color.RED(0.20),
    title='Risk Zone'
)

@plot.fill(
    'entry', 'tp',
    color=color.GREEN(0.20),
    title='Reward Zone'
)

@plot.marker(
    style=plot.marker_style.CROSS,
    position=plot.marker_position.CENTER,
    size=7,
    title='Entry Signal'
)


# ============================================================
# MAIN STRATEGY
# ============================================================

class Main(MainContext):

    def __init__(
        self,
        risk_reward,
        account_capital,
        risk_percent,
        risk_buffer_percent,
        contract_size,
        adaptive_trailing_enabled,
        break_even_buffer,
        delete_setup,
        delete_bar_index,
        manual_exit_bar_index,
        show_bar_index,
        show_entry_descriptions,
        show_daily_report,
        show_monthly_daily_breakdown,
        report_date
    ):

        self.risk_reward = risk_reward
        self.account_capital = account_capital
        self.risk_percent = risk_percent
        self.risk_buffer_percent = risk_buffer_percent
        self.contract_size = contract_size
        self.adaptive_trailing_enabled = adaptive_trailing_enabled
        self.break_even_buffer = break_even_buffer
        self.delete_setup = delete_setup
        self.delete_bar_index = delete_bar_index
        self.manual_exit_bar_index = manual_exit_bar_index
        self.show_bar_index = show_bar_index
        self.show_entry_descriptions = show_entry_descriptions
        self.show_daily_report = show_daily_report
        self.show_monthly_daily_breakdown = show_monthly_daily_breakdown

        # Custom report date: YYYYMMDD. The selected date drives daily P/L;
        # its month drives monthly P/L and the daily breakdown.
        report_date = int(report_date)
        report_year = int(report_date / 10000)
        report_month = int((report_date % 10000) / 100)
        report_day = int(report_date % 100)

        if report_month < 1:
            report_month = 1
        elif report_month > 12:
            report_month = 12

        month_days = 31
        if report_month == 2:
            month_days = 28
            if (report_year % 4 == 0 and report_year % 100 != 0) or report_year % 400 == 0:
                month_days = 29
        elif (
            report_month == 4
            or report_month == 6
            or report_month == 9
            or report_month == 11
        ):
            month_days = 30

        if report_day < 1:
            report_day = 1
        elif report_day > month_days:
            report_day = month_days

        self.report_date = report_year * 10000 + report_month * 100 + report_day

        # Convert selected IST calendar date to an epoch-day key.
        adjusted_year = report_year
        if report_month <= 2:
            adjusted_year = adjusted_year - 1
        era = int(adjusted_year / 400)
        year_of_era = adjusted_year - era * 400
        shifted_month = report_month + 9
        if report_month > 2:
            shifted_month = report_month - 3
        day_of_year = int((153 * shifted_month + 2) / 5) + report_day - 1
        day_of_era = (year_of_era * 365 + int(year_of_era / 4)
                      - int(year_of_era / 100) + day_of_year)
        self._selected_report_day_key = float(era * 146097 + day_of_era - 719468)

        self._selected_report_month_start_key = (
            self._selected_report_day_key - (report_day - 1)
        )
        self._selected_report_month_end_key = (
            self._selected_report_month_start_key + month_days
        )

        self._daily_report_label = LabelRel(
            '',
            RelativePosition(
                vertical_anchor=va.TOP,
                horizontal_anchor=ha.RIGHT,
                top_bottom_ratio=0.05,
                left_right_ratio=0.7
            ),
            text_color=color.BLACK,
            bg_color=color.TRANSPARENT,
            font_size=12
        )

        chart_minutes = self.time_frame.to_minutes()

        confirmation_tf = TimeFrame.from_str('15m')

        if chart_minutes == 1:
            confirmation_tf = TimeFrame.from_str('3m')
        elif chart_minutes == 3:
            confirmation_tf = TimeFrame.from_str('5m')
        elif chart_minutes == 5:
            confirmation_tf = TimeFrame.from_str('15m')

        self._htf_ema20, self._htf_ema50 = self.calc_on(
            ConfirmHtfEma,
            time_frame=confirmation_tf
        )

        self._is_3m_chart = chart_minutes == 3
        self._is_m1_chart = chart_minutes == 1

        (
            self._m5_open,
            self._m5_close,
            self._m5_volume,
            self._m5_average_volume
        ) = self.calc_on(
            ConfirmCandle,
            time_frame=TimeFrame.from_str('5m')
        )

        (
            self._m15_open,
            self._m15_close,
            self._m15_volume,
            self._m15_average_volume
        ) = self.calc_on(
            ConfirmCandle,
            time_frame=TimeFrame.from_str('15m')
        )

    def calc(self):

        # ====================================================
        # TRADE STATE
        # ====================================================

        entry = MutSeriesF.new(init=nan)
        second_entry_price = MutSeriesF.new(init=nan)
        third_entry_price = MutSeriesF.new(init=nan)
        fourth_entry_price = MutSeriesF.new(init=nan)
        fifth_entry_price = MutSeriesF.new(init=nan)

        sl = MutSeriesF.new(init=nan)
        tp = MutSeriesF.new(init=nan)

        side = MutSeriesF.new(init=0.0)
        trade_lot = MutSeriesF.new(init=nan)
        trade_risk_cash = MutSeriesF.new(init=nan)

        # Midpoint-first two-leg execution. The midpoint is the first fill;
        # the optional immediate leg is sized only from remaining dollar risk.
        midpoint_master_entry = MutSeriesF.new(init=nan)
        early_leg_entry = MutSeriesF.new(init=nan)
        early_leg_lot = MutSeriesF.new(init=nan)
        mid_leg_lot = MutSeriesF.new(init=nan)
        mid_leg_active = MutSeriesF.new(init=0.0)
        pending_mid_entry = MutSeriesF.new(init=nan)
        pending_early_entry = MutSeriesF.new(init=nan)
        early_leg_closed = MutSeriesF.new(init=0.0)
        mid_leg_pnl = MutSeriesF.new(init=0.0)
        early_leg_pnl = MutSeriesF.new(init=0.0)
        setup_risk_budget = MutSeriesF.new(init=nan)

        # Adaptive trailing state: all prices are simulated indicator levels.
        original_risk_distance = MutSeriesF.new(init=nan)
        favorable_extreme = MutSeriesF.new(init=nan)
        trail_candidate = MutSeriesF.new(init=nan)
        trail_confirm_count = MutSeriesF.new(init=0.0)
        trail_stage = MutSeriesF.new(init=0.0)
        trail_last_update_bar = MutSeriesF.new(init=-1.0)

        entry_count = MutSeriesF.new(init=0.0)
        last_entry_bar = MutSeriesF.new(init=-1.0)
        last_entry_price = MutSeriesF.new(init=nan)

        # Pending Entry 1 lifecycle. A setup is not active until a later
        # completed candle reaches its planned midpoint entry.
        pending_trade_side = MutSeriesF.new(init=0.0)
        pending_trade_entry = MutSeriesF.new(init=nan)
        pending_trade_sl = MutSeriesF.new(init=nan)
        pending_trade_tp = MutSeriesF.new(init=nan)
        pending_trade_lot = MutSeriesF.new(init=nan)
        pending_trade_risk_cash = MutSeriesF.new(init=nan)
        pending_trade_setup_day = MutSeriesF.new(init=nan)
        pending_trade_setup_bar = MutSeriesF.new(init=-1.0)

        # Independent multi-slot original-midpoint report tracker.
        # Multiple unresolved setups can coexist with a live early leg.
        count_1_side = MutSeriesF.new(init=0.0)
        count_1_entry = MutSeriesF.new(init=nan)
        count_1_sl = MutSeriesF.new(init=nan)
        count_1_tp = MutSeriesF.new(init=nan)
        count_1_day = MutSeriesF.new(init=nan)
        count_1_bar = MutSeriesF.new(init=-1.0)
        count_2_side = MutSeriesF.new(init=0.0)
        count_2_entry = MutSeriesF.new(init=nan)
        count_2_sl = MutSeriesF.new(init=nan)
        count_2_tp = MutSeriesF.new(init=nan)
        count_2_day = MutSeriesF.new(init=nan)
        count_2_bar = MutSeriesF.new(init=-1.0)
        count_3_side = MutSeriesF.new(init=0.0)
        count_3_entry = MutSeriesF.new(init=nan)
        count_3_sl = MutSeriesF.new(init=nan)
        count_3_tp = MutSeriesF.new(init=nan)
        count_3_day = MutSeriesF.new(init=nan)
        count_3_bar = MutSeriesF.new(init=-1.0)
        count_4_side = MutSeriesF.new(init=0.0)
        count_4_entry = MutSeriesF.new(init=nan)
        count_4_sl = MutSeriesF.new(init=nan)
        count_4_tp = MutSeriesF.new(init=nan)
        count_4_day = MutSeriesF.new(init=nan)
        count_4_bar = MutSeriesF.new(init=-1.0)
        count_5_side = MutSeriesF.new(init=0.0)
        count_5_entry = MutSeriesF.new(init=nan)
        count_5_sl = MutSeriesF.new(init=nan)
        count_5_tp = MutSeriesF.new(init=nan)
        count_5_day = MutSeriesF.new(init=nan)
        count_5_bar = MutSeriesF.new(init=-1.0)
        count_6_side = MutSeriesF.new(init=0.0)
        count_6_entry = MutSeriesF.new(init=nan)
        count_6_sl = MutSeriesF.new(init=nan)
        count_6_tp = MutSeriesF.new(init=nan)
        count_6_day = MutSeriesF.new(init=nan)
        count_6_bar = MutSeriesF.new(init=-1.0)
        count_7_side = MutSeriesF.new(init=0.0)
        count_7_entry = MutSeriesF.new(init=nan)
        count_7_sl = MutSeriesF.new(init=nan)
        count_7_tp = MutSeriesF.new(init=nan)
        count_7_day = MutSeriesF.new(init=nan)
        count_7_bar = MutSeriesF.new(init=-1.0)
        count_8_side = MutSeriesF.new(init=0.0)
        count_8_entry = MutSeriesF.new(init=nan)
        count_8_sl = MutSeriesF.new(init=nan)
        count_8_tp = MutSeriesF.new(init=nan)
        count_8_day = MutSeriesF.new(init=nan)
        count_8_bar = MutSeriesF.new(init=-1.0)
        count_9_side = MutSeriesF.new(init=0.0)
        count_9_entry = MutSeriesF.new(init=nan)
        count_9_sl = MutSeriesF.new(init=nan)
        count_9_tp = MutSeriesF.new(init=nan)
        count_9_day = MutSeriesF.new(init=nan)
        count_9_bar = MutSeriesF.new(init=-1.0)
        count_10_side = MutSeriesF.new(init=0.0)
        count_10_entry = MutSeriesF.new(init=nan)
        count_10_sl = MutSeriesF.new(init=nan)
        count_10_tp = MutSeriesF.new(init=nan)
        count_10_day = MutSeriesF.new(init=nan)
        count_10_bar = MutSeriesF.new(init=-1.0)
        count_11_side = MutSeriesF.new(init=0.0)
        count_11_entry = MutSeriesF.new(init=nan)
        count_11_sl = MutSeriesF.new(init=nan)
        count_11_tp = MutSeriesF.new(init=nan)
        count_11_day = MutSeriesF.new(init=nan)
        count_11_bar = MutSeriesF.new(init=-1.0)
        count_12_side = MutSeriesF.new(init=0.0)
        count_12_entry = MutSeriesF.new(init=nan)
        count_12_sl = MutSeriesF.new(init=nan)
        count_12_tp = MutSeriesF.new(init=nan)
        count_12_day = MutSeriesF.new(init=nan)
        count_12_bar = MutSeriesF.new(init=-1.0)
        count_13_side = MutSeriesF.new(init=0.0)
        count_13_entry = MutSeriesF.new(init=nan)
        count_13_sl = MutSeriesF.new(init=nan)
        count_13_tp = MutSeriesF.new(init=nan)
        count_13_day = MutSeriesF.new(init=nan)
        count_13_bar = MutSeriesF.new(init=-1.0)
        count_14_side = MutSeriesF.new(init=0.0)
        count_14_entry = MutSeriesF.new(init=nan)
        count_14_sl = MutSeriesF.new(init=nan)
        count_14_tp = MutSeriesF.new(init=nan)
        count_14_day = MutSeriesF.new(init=nan)
        count_14_bar = MutSeriesF.new(init=-1.0)
        count_15_side = MutSeriesF.new(init=0.0)
        count_15_entry = MutSeriesF.new(init=nan)
        count_15_sl = MutSeriesF.new(init=nan)
        count_15_tp = MutSeriesF.new(init=nan)
        count_15_day = MutSeriesF.new(init=nan)
        count_15_bar = MutSeriesF.new(init=-1.0)
        count_16_side = MutSeriesF.new(init=0.0)
        count_16_entry = MutSeriesF.new(init=nan)
        count_16_sl = MutSeriesF.new(init=nan)
        count_16_tp = MutSeriesF.new(init=nan)
        count_16_day = MutSeriesF.new(init=nan)
        count_16_bar = MutSeriesF.new(init=-1.0)
        count_17_side = MutSeriesF.new(init=0.0)
        count_17_entry = MutSeriesF.new(init=nan)
        count_17_sl = MutSeriesF.new(init=nan)
        count_17_tp = MutSeriesF.new(init=nan)
        count_17_day = MutSeriesF.new(init=nan)
        count_17_bar = MutSeriesF.new(init=-1.0)
        count_18_side = MutSeriesF.new(init=0.0)
        count_18_entry = MutSeriesF.new(init=nan)
        count_18_sl = MutSeriesF.new(init=nan)
        count_18_tp = MutSeriesF.new(init=nan)
        count_18_day = MutSeriesF.new(init=nan)
        count_18_bar = MutSeriesF.new(init=-1.0)
        count_19_side = MutSeriesF.new(init=0.0)
        count_19_entry = MutSeriesF.new(init=nan)
        count_19_sl = MutSeriesF.new(init=nan)
        count_19_tp = MutSeriesF.new(init=nan)
        count_19_day = MutSeriesF.new(init=nan)
        count_19_bar = MutSeriesF.new(init=-1.0)
        count_20_side = MutSeriesF.new(init=0.0)
        count_20_entry = MutSeriesF.new(init=nan)
        count_20_sl = MutSeriesF.new(init=nan)
        count_20_tp = MutSeriesF.new(init=nan)
        count_20_day = MutSeriesF.new(init=nan)
        count_20_bar = MutSeriesF.new(init=-1.0)


        entry_label_time = MutSeriesF.new(init=nan)
        early_exit_warned = MutSeriesF.new(init=0.0)

        report_trades = MutSeriesF.new(init=0.0)
        report_active_trades = MutSeriesF.new(init=0.0)
        report_inactive_trades = MutSeriesF.new(init=0.0)
        report_active_pnl = MutSeriesF.new(init=0.0)
        report_inactive_pnl = MutSeriesF.new(init=0.0)
        report_sl = MutSeriesF.new(init=0.0)
        report_tp = MutSeriesF.new(init=0.0)
        report_trailing_sl = MutSeriesF.new(init=0.0)
        report_net_profit = MutSeriesF.new(init=0.0)
        monthly_net_profit = MutSeriesF.new(init=0.0)
        monthly_day_01_profit = MutSeriesF.new(init=0.0)
        monthly_day_02_profit = MutSeriesF.new(init=0.0)
        monthly_day_03_profit = MutSeriesF.new(init=0.0)
        monthly_day_04_profit = MutSeriesF.new(init=0.0)
        monthly_day_05_profit = MutSeriesF.new(init=0.0)
        monthly_day_06_profit = MutSeriesF.new(init=0.0)
        monthly_day_07_profit = MutSeriesF.new(init=0.0)
        monthly_day_08_profit = MutSeriesF.new(init=0.0)
        monthly_day_09_profit = MutSeriesF.new(init=0.0)
        monthly_day_10_profit = MutSeriesF.new(init=0.0)
        monthly_day_11_profit = MutSeriesF.new(init=0.0)
        monthly_day_12_profit = MutSeriesF.new(init=0.0)
        monthly_day_13_profit = MutSeriesF.new(init=0.0)
        monthly_day_14_profit = MutSeriesF.new(init=0.0)
        monthly_day_15_profit = MutSeriesF.new(init=0.0)
        monthly_day_16_profit = MutSeriesF.new(init=0.0)
        monthly_day_17_profit = MutSeriesF.new(init=0.0)
        monthly_day_18_profit = MutSeriesF.new(init=0.0)
        monthly_day_19_profit = MutSeriesF.new(init=0.0)
        monthly_day_20_profit = MutSeriesF.new(init=0.0)
        monthly_day_21_profit = MutSeriesF.new(init=0.0)
        monthly_day_22_profit = MutSeriesF.new(init=0.0)
        monthly_day_23_profit = MutSeriesF.new(init=0.0)
        monthly_day_24_profit = MutSeriesF.new(init=0.0)
        monthly_day_25_profit = MutSeriesF.new(init=0.0)
        monthly_day_26_profit = MutSeriesF.new(init=0.0)
        monthly_day_27_profit = MutSeriesF.new(init=0.0)
        monthly_day_28_profit = MutSeriesF.new(init=0.0)
        monthly_day_29_profit = MutSeriesF.new(init=0.0)
        monthly_day_30_profit = MutSeriesF.new(init=0.0)
        monthly_day_31_profit = MutSeriesF.new(init=0.0)
        report_rr_setting = MutSeriesF.new(init=nan)

        # Daily capital protection state, based on IST day and closed active-trade P/L.
        risk_day_key = MutSeriesF.new(init=nan)
        daily_start_balance = MutSeriesF.new(init=nan)
        daily_realized_pnl = MutSeriesF.new(init=0.0)
        reduced_risk_mode = MutSeriesF.new(init=0.0)

        entry_price = nan
        stop_price = nan
        risk = nan
        target_price = nan

        # Daily risk mode is updated after closed-trade P/L is processed below.
        normal_risk_percent = min(7.0, self.risk_percent + self.risk_buffer_percent)
        reduced_risk_percent = 4.0  # 3% target + 1% additional buffer
        total_risk_percent = normal_risk_percent
        risk_budget_cash = self.account_capital * total_risk_percent / 100.0

        risk_per_one_lot = nan
        calculated_lot = 0.0
        calculated_risk_cash = nan
        sl_distance = nan
        realized_exit_price = nan
        realized_pnl = nan

        maximum_allowed_sl_distance = 15.0

        buy_breakout_pullback_ready = False
        buy_breakout_entry_price = nan

        sell_breakout_pullback_ready = False
        sell_breakout_entry_price = nan

        buy_average_touched = False
        buy_bottom_touched = False
        sell_average_touched = False
        sell_top_touched = False

        bullish_pullback_confirmation = False
        bearish_pullback_confirmation = False

        pending_buy = MutSeriesF.new(init=0.0)
        pending_buy_average = MutSeriesF.new(init=nan)
        pending_buy_low = MutSeriesF.new(init=nan)
        pending_buy_bar = MutSeriesF.new(init=-1.0)

        pending_sell = MutSeriesF.new(init=0.0)
        pending_sell_average = MutSeriesF.new(init=nan)
        pending_sell_high = MutSeriesF.new(init=nan)
        pending_sell_bar = MutSeriesF.new(init=-1.0)

        if self.bar_index > 0:

            entry[0] = entry[1]
            second_entry_price[0] = second_entry_price[1]
            third_entry_price[0] = third_entry_price[1]
            fourth_entry_price[0] = fourth_entry_price[1]
            fifth_entry_price[0] = fifth_entry_price[1]

            sl[0] = sl[1]
            tp[0] = tp[1]

            side[0] = side[1]
            trade_lot[0] = trade_lot[1]
            trade_risk_cash[0] = trade_risk_cash[1]

            midpoint_master_entry[0] = midpoint_master_entry[1]
            early_leg_entry[0] = early_leg_entry[1]
            early_leg_lot[0] = early_leg_lot[1]
            mid_leg_lot[0] = mid_leg_lot[1]
            mid_leg_active[0] = mid_leg_active[1]
            pending_mid_entry[0] = pending_mid_entry[1]
            pending_early_entry[0] = pending_early_entry[1]
            early_leg_closed[0] = early_leg_closed[1]
            mid_leg_pnl[0] = mid_leg_pnl[1]
            early_leg_pnl[0] = early_leg_pnl[1]
            setup_risk_budget[0] = setup_risk_budget[1]

            original_risk_distance[0] = original_risk_distance[1]
            favorable_extreme[0] = favorable_extreme[1]
            trail_candidate[0] = trail_candidate[1]
            trail_confirm_count[0] = trail_confirm_count[1]
            trail_stage[0] = trail_stage[1]
            trail_last_update_bar[0] = trail_last_update_bar[1]

            entry_count[0] = entry_count[1]
            last_entry_bar[0] = last_entry_bar[1]
            last_entry_price[0] = last_entry_price[1]

            pending_trade_side[0] = pending_trade_side[1]
            pending_trade_entry[0] = pending_trade_entry[1]
            pending_trade_sl[0] = pending_trade_sl[1]
            pending_trade_tp[0] = pending_trade_tp[1]
            pending_trade_lot[0] = pending_trade_lot[1]
            pending_trade_risk_cash[0] = pending_trade_risk_cash[1]
            pending_trade_setup_day[0] = pending_trade_setup_day[1]
            pending_trade_setup_bar[0] = pending_trade_setup_bar[1]

            count_1_side[0] = count_1_side[1]
            count_1_entry[0] = count_1_entry[1]
            count_1_sl[0] = count_1_sl[1]
            count_1_tp[0] = count_1_tp[1]
            count_1_day[0] = count_1_day[1]
            count_1_bar[0] = count_1_bar[1]
            count_2_side[0] = count_2_side[1]
            count_2_entry[0] = count_2_entry[1]
            count_2_sl[0] = count_2_sl[1]
            count_2_tp[0] = count_2_tp[1]
            count_2_day[0] = count_2_day[1]
            count_2_bar[0] = count_2_bar[1]
            count_3_side[0] = count_3_side[1]
            count_3_entry[0] = count_3_entry[1]
            count_3_sl[0] = count_3_sl[1]
            count_3_tp[0] = count_3_tp[1]
            count_3_day[0] = count_3_day[1]
            count_3_bar[0] = count_3_bar[1]
            count_4_side[0] = count_4_side[1]
            count_4_entry[0] = count_4_entry[1]
            count_4_sl[0] = count_4_sl[1]
            count_4_tp[0] = count_4_tp[1]
            count_4_day[0] = count_4_day[1]
            count_4_bar[0] = count_4_bar[1]
            count_5_side[0] = count_5_side[1]
            count_5_entry[0] = count_5_entry[1]
            count_5_sl[0] = count_5_sl[1]
            count_5_tp[0] = count_5_tp[1]
            count_5_day[0] = count_5_day[1]
            count_5_bar[0] = count_5_bar[1]
            count_6_side[0] = count_6_side[1]
            count_6_entry[0] = count_6_entry[1]
            count_6_sl[0] = count_6_sl[1]
            count_6_tp[0] = count_6_tp[1]
            count_6_day[0] = count_6_day[1]
            count_6_bar[0] = count_6_bar[1]
            count_7_side[0] = count_7_side[1]
            count_7_entry[0] = count_7_entry[1]
            count_7_sl[0] = count_7_sl[1]
            count_7_tp[0] = count_7_tp[1]
            count_7_day[0] = count_7_day[1]
            count_7_bar[0] = count_7_bar[1]
            count_8_side[0] = count_8_side[1]
            count_8_entry[0] = count_8_entry[1]
            count_8_sl[0] = count_8_sl[1]
            count_8_tp[0] = count_8_tp[1]
            count_8_day[0] = count_8_day[1]
            count_8_bar[0] = count_8_bar[1]
            count_9_side[0] = count_9_side[1]
            count_9_entry[0] = count_9_entry[1]
            count_9_sl[0] = count_9_sl[1]
            count_9_tp[0] = count_9_tp[1]
            count_9_day[0] = count_9_day[1]
            count_9_bar[0] = count_9_bar[1]
            count_10_side[0] = count_10_side[1]
            count_10_entry[0] = count_10_entry[1]
            count_10_sl[0] = count_10_sl[1]
            count_10_tp[0] = count_10_tp[1]
            count_10_day[0] = count_10_day[1]
            count_10_bar[0] = count_10_bar[1]
            count_11_side[0] = count_11_side[1]
            count_11_entry[0] = count_11_entry[1]
            count_11_sl[0] = count_11_sl[1]
            count_11_tp[0] = count_11_tp[1]
            count_11_day[0] = count_11_day[1]
            count_11_bar[0] = count_11_bar[1]
            count_12_side[0] = count_12_side[1]
            count_12_entry[0] = count_12_entry[1]
            count_12_sl[0] = count_12_sl[1]
            count_12_tp[0] = count_12_tp[1]
            count_12_day[0] = count_12_day[1]
            count_12_bar[0] = count_12_bar[1]
            count_13_side[0] = count_13_side[1]
            count_13_entry[0] = count_13_entry[1]
            count_13_sl[0] = count_13_sl[1]
            count_13_tp[0] = count_13_tp[1]
            count_13_day[0] = count_13_day[1]
            count_13_bar[0] = count_13_bar[1]
            count_14_side[0] = count_14_side[1]
            count_14_entry[0] = count_14_entry[1]
            count_14_sl[0] = count_14_sl[1]
            count_14_tp[0] = count_14_tp[1]
            count_14_day[0] = count_14_day[1]
            count_14_bar[0] = count_14_bar[1]
            count_15_side[0] = count_15_side[1]
            count_15_entry[0] = count_15_entry[1]
            count_15_sl[0] = count_15_sl[1]
            count_15_tp[0] = count_15_tp[1]
            count_15_day[0] = count_15_day[1]
            count_15_bar[0] = count_15_bar[1]
            count_16_side[0] = count_16_side[1]
            count_16_entry[0] = count_16_entry[1]
            count_16_sl[0] = count_16_sl[1]
            count_16_tp[0] = count_16_tp[1]
            count_16_day[0] = count_16_day[1]
            count_16_bar[0] = count_16_bar[1]
            count_17_side[0] = count_17_side[1]
            count_17_entry[0] = count_17_entry[1]
            count_17_sl[0] = count_17_sl[1]
            count_17_tp[0] = count_17_tp[1]
            count_17_day[0] = count_17_day[1]
            count_17_bar[0] = count_17_bar[1]
            count_18_side[0] = count_18_side[1]
            count_18_entry[0] = count_18_entry[1]
            count_18_sl[0] = count_18_sl[1]
            count_18_tp[0] = count_18_tp[1]
            count_18_day[0] = count_18_day[1]
            count_18_bar[0] = count_18_bar[1]
            count_19_side[0] = count_19_side[1]
            count_19_entry[0] = count_19_entry[1]
            count_19_sl[0] = count_19_sl[1]
            count_19_tp[0] = count_19_tp[1]
            count_19_day[0] = count_19_day[1]
            count_19_bar[0] = count_19_bar[1]
            count_20_side[0] = count_20_side[1]
            count_20_entry[0] = count_20_entry[1]
            count_20_sl[0] = count_20_sl[1]
            count_20_tp[0] = count_20_tp[1]
            count_20_day[0] = count_20_day[1]
            count_20_bar[0] = count_20_bar[1]

            entry_label_time[0] = entry_label_time[1]
            early_exit_warned[0] = early_exit_warned[1]

            report_trades[0] = report_trades[1]
            report_active_trades[0] = report_active_trades[1]
            report_inactive_trades[0] = report_inactive_trades[1]
            report_active_pnl[0] = report_active_pnl[1]
            report_inactive_pnl[0] = report_inactive_pnl[1]
            report_sl[0] = report_sl[1]
            report_tp[0] = report_tp[1]
            report_trailing_sl[0] = report_trailing_sl[1]
            report_net_profit[0] = report_net_profit[1]
            monthly_net_profit[0] = monthly_net_profit[1]
            monthly_day_01_profit[0] = monthly_day_01_profit[1]
            monthly_day_02_profit[0] = monthly_day_02_profit[1]
            monthly_day_03_profit[0] = monthly_day_03_profit[1]
            monthly_day_04_profit[0] = monthly_day_04_profit[1]
            monthly_day_05_profit[0] = monthly_day_05_profit[1]
            monthly_day_06_profit[0] = monthly_day_06_profit[1]
            monthly_day_07_profit[0] = monthly_day_07_profit[1]
            monthly_day_08_profit[0] = monthly_day_08_profit[1]
            monthly_day_09_profit[0] = monthly_day_09_profit[1]
            monthly_day_10_profit[0] = monthly_day_10_profit[1]
            monthly_day_11_profit[0] = monthly_day_11_profit[1]
            monthly_day_12_profit[0] = monthly_day_12_profit[1]
            monthly_day_13_profit[0] = monthly_day_13_profit[1]
            monthly_day_14_profit[0] = monthly_day_14_profit[1]
            monthly_day_15_profit[0] = monthly_day_15_profit[1]
            monthly_day_16_profit[0] = monthly_day_16_profit[1]
            monthly_day_17_profit[0] = monthly_day_17_profit[1]
            monthly_day_18_profit[0] = monthly_day_18_profit[1]
            monthly_day_19_profit[0] = monthly_day_19_profit[1]
            monthly_day_20_profit[0] = monthly_day_20_profit[1]
            monthly_day_21_profit[0] = monthly_day_21_profit[1]
            monthly_day_22_profit[0] = monthly_day_22_profit[1]
            monthly_day_23_profit[0] = monthly_day_23_profit[1]
            monthly_day_24_profit[0] = monthly_day_24_profit[1]
            monthly_day_25_profit[0] = monthly_day_25_profit[1]
            monthly_day_26_profit[0] = monthly_day_26_profit[1]
            monthly_day_27_profit[0] = monthly_day_27_profit[1]
            monthly_day_28_profit[0] = monthly_day_28_profit[1]
            monthly_day_29_profit[0] = monthly_day_29_profit[1]
            monthly_day_30_profit[0] = monthly_day_30_profit[1]
            monthly_day_31_profit[0] = monthly_day_31_profit[1]
            report_rr_setting[0] = report_rr_setting[1]

            risk_day_key[0] = risk_day_key[1]
            daily_start_balance[0] = daily_start_balance[1]
            daily_realized_pnl[0] = daily_realized_pnl[1]
            reduced_risk_mode[0] = reduced_risk_mode[1]

            pending_buy[0] = pending_buy[1]
            pending_buy_average[0] = pending_buy_average[1]
            pending_buy_low[0] = pending_buy_low[1]
            pending_buy_bar[0] = pending_buy_bar[1]

            pending_sell[0] = pending_sell[1]
            pending_sell_average[0] = pending_sell_average[1]
            pending_sell_high[0] = pending_sell_high[1]
            pending_sell_bar[0] = pending_sell_bar[1]

        # ====================================================
        # INDICATORS
        # ====================================================

        ema9 = Ema.new(self.close, 9)
        ema20 = Ema.new(self.close, 20)
        ema50 = Ema.new(self.close, 50)
        ema200 = Ema.new(self.close, 200)

        rsi = Rsi.new(self.close, 14)

        # Adaptive trailing indicators (the manager is enabled only on M1).
        trail_ema9 = ema9
        trail_ema21 = Ema.new(self.close, 21)
        atr14 = Atr.new(14)
        minus_di, adx14, plus_di = Adx.new(14, 14)

        # ====================================================
        # RISK REWARD
        # ====================================================

        rr_multiplier = 2.0

        if self.risk_reward == '1:1':
            rr_multiplier = 1.0
        elif self.risk_reward == '1:1.5':
            rr_multiplier = 1.5
        elif self.risk_reward == '1:2':
            rr_multiplier = 2.0
        elif self.risk_reward == '1:3':
            rr_multiplier = 3.0
        elif self.risk_reward == '1:4':
            rr_multiplier = 4.0

        # ====================================================
        # REBUILD TRADE HISTORY WHEN RISK:REWARD CHANGES
        # ====================================================

        rr_setting_changed = False
        if self.bar_index > 0:
            rr_setting_changed = (
                report_rr_setting[1] != rr_multiplier
            )

        if rr_setting_changed:
            entry[0] = nan
            second_entry_price[0] = nan
            third_entry_price[0] = nan
            fourth_entry_price[0] = nan
            fifth_entry_price[0] = nan
            sl[0] = nan
            tp[0] = nan
            side[0] = 0.0
            trade_lot[0] = nan
            trade_risk_cash[0] = nan
            midpoint_master_entry[0] = nan
            early_leg_entry[0] = nan
            early_leg_lot[0] = nan
            mid_leg_lot[0] = nan
            mid_leg_active[0] = 0.0
            pending_mid_entry[0] = nan
            pending_early_entry[0] = nan
            early_leg_closed[0] = 0.0
            mid_leg_pnl[0] = 0.0
            early_leg_pnl[0] = 0.0
            setup_risk_budget[0] = nan
            original_risk_distance[0] = nan
            favorable_extreme[0] = nan
            trail_candidate[0] = nan
            trail_confirm_count[0] = 0.0
            trail_stage[0] = 0.0
            trail_last_update_bar[0] = -1.0
            entry_count[0] = 0.0
            last_entry_bar[0] = -1.0
            last_entry_price[0] = nan
            pending_trade_side[0] = 0.0
            pending_trade_entry[0] = nan
            pending_trade_sl[0] = nan
            pending_trade_tp[0] = nan
            pending_trade_lot[0] = nan
            pending_trade_risk_cash[0] = nan
            pending_trade_setup_day[0] = nan
            pending_trade_setup_bar[0] = -1.0
            count_1_side[0] = 0.0
            count_1_entry[0] = nan
            count_1_sl[0] = nan
            count_1_tp[0] = nan
            count_1_day[0] = nan
            count_1_bar[0] = -1.0
            count_2_side[0] = 0.0
            count_2_entry[0] = nan
            count_2_sl[0] = nan
            count_2_tp[0] = nan
            count_2_day[0] = nan
            count_2_bar[0] = -1.0
            count_3_side[0] = 0.0
            count_3_entry[0] = nan
            count_3_sl[0] = nan
            count_3_tp[0] = nan
            count_3_day[0] = nan
            count_3_bar[0] = -1.0
            count_4_side[0] = 0.0
            count_4_entry[0] = nan
            count_4_sl[0] = nan
            count_4_tp[0] = nan
            count_4_day[0] = nan
            count_4_bar[0] = -1.0
            count_5_side[0] = 0.0
            count_5_entry[0] = nan
            count_5_sl[0] = nan
            count_5_tp[0] = nan
            count_5_day[0] = nan
            count_5_bar[0] = -1.0
            count_6_side[0] = 0.0
            count_6_entry[0] = nan
            count_6_sl[0] = nan
            count_6_tp[0] = nan
            count_6_day[0] = nan
            count_6_bar[0] = -1.0
            count_7_side[0] = 0.0
            count_7_entry[0] = nan
            count_7_sl[0] = nan
            count_7_tp[0] = nan
            count_7_day[0] = nan
            count_7_bar[0] = -1.0
            count_8_side[0] = 0.0
            count_8_entry[0] = nan
            count_8_sl[0] = nan
            count_8_tp[0] = nan
            count_8_day[0] = nan
            count_8_bar[0] = -1.0
            count_9_side[0] = 0.0
            count_9_entry[0] = nan
            count_9_sl[0] = nan
            count_9_tp[0] = nan
            count_9_day[0] = nan
            count_9_bar[0] = -1.0
            count_10_side[0] = 0.0
            count_10_entry[0] = nan
            count_10_sl[0] = nan
            count_10_tp[0] = nan
            count_10_day[0] = nan
            count_10_bar[0] = -1.0
            count_11_side[0] = 0.0
            count_11_entry[0] = nan
            count_11_sl[0] = nan
            count_11_tp[0] = nan
            count_11_day[0] = nan
            count_11_bar[0] = -1.0
            count_12_side[0] = 0.0
            count_12_entry[0] = nan
            count_12_sl[0] = nan
            count_12_tp[0] = nan
            count_12_day[0] = nan
            count_12_bar[0] = -1.0
            count_13_side[0] = 0.0
            count_13_entry[0] = nan
            count_13_sl[0] = nan
            count_13_tp[0] = nan
            count_13_day[0] = nan
            count_13_bar[0] = -1.0
            count_14_side[0] = 0.0
            count_14_entry[0] = nan
            count_14_sl[0] = nan
            count_14_tp[0] = nan
            count_14_day[0] = nan
            count_14_bar[0] = -1.0
            count_15_side[0] = 0.0
            count_15_entry[0] = nan
            count_15_sl[0] = nan
            count_15_tp[0] = nan
            count_15_day[0] = nan
            count_15_bar[0] = -1.0
            count_16_side[0] = 0.0
            count_16_entry[0] = nan
            count_16_sl[0] = nan
            count_16_tp[0] = nan
            count_16_day[0] = nan
            count_16_bar[0] = -1.0
            count_17_side[0] = 0.0
            count_17_entry[0] = nan
            count_17_sl[0] = nan
            count_17_tp[0] = nan
            count_17_day[0] = nan
            count_17_bar[0] = -1.0
            count_18_side[0] = 0.0
            count_18_entry[0] = nan
            count_18_sl[0] = nan
            count_18_tp[0] = nan
            count_18_day[0] = nan
            count_18_bar[0] = -1.0
            count_19_side[0] = 0.0
            count_19_entry[0] = nan
            count_19_sl[0] = nan
            count_19_tp[0] = nan
            count_19_day[0] = nan
            count_19_bar[0] = -1.0
            count_20_side[0] = 0.0
            count_20_entry[0] = nan
            count_20_sl[0] = nan
            count_20_tp[0] = nan
            count_20_day[0] = nan
            count_20_bar[0] = -1.0
            entry_label_time[0] = nan
            early_exit_warned[0] = 0.0
            report_trades[0] = 0.0
            report_active_trades[0] = 0.0
            report_inactive_trades[0] = 0.0
            report_active_pnl[0] = 0.0
            report_inactive_pnl[0] = 0.0
            report_sl[0] = 0.0
            report_tp[0] = 0.0
            report_trailing_sl[0] = 0.0
            report_net_profit[0] = 0.0
            monthly_net_profit[0] = 0.0
            monthly_day_01_profit[0] = 0.0
            monthly_day_02_profit[0] = 0.0
            monthly_day_03_profit[0] = 0.0
            monthly_day_04_profit[0] = 0.0
            monthly_day_05_profit[0] = 0.0
            monthly_day_06_profit[0] = 0.0
            monthly_day_07_profit[0] = 0.0
            monthly_day_08_profit[0] = 0.0
            monthly_day_09_profit[0] = 0.0
            monthly_day_10_profit[0] = 0.0
            monthly_day_11_profit[0] = 0.0
            monthly_day_12_profit[0] = 0.0
            monthly_day_13_profit[0] = 0.0
            monthly_day_14_profit[0] = 0.0
            monthly_day_15_profit[0] = 0.0
            monthly_day_16_profit[0] = 0.0
            monthly_day_17_profit[0] = 0.0
            monthly_day_18_profit[0] = 0.0
            monthly_day_19_profit[0] = 0.0
            monthly_day_20_profit[0] = 0.0
            monthly_day_21_profit[0] = 0.0
            monthly_day_22_profit[0] = 0.0
            monthly_day_23_profit[0] = 0.0
            monthly_day_24_profit[0] = 0.0
            monthly_day_25_profit[0] = 0.0
            monthly_day_26_profit[0] = 0.0
            monthly_day_27_profit[0] = 0.0
            monthly_day_28_profit[0] = 0.0
            monthly_day_29_profit[0] = 0.0
            monthly_day_30_profit[0] = 0.0
            monthly_day_31_profit[0] = 0.0
            pending_buy[0] = 0.0
            pending_buy_average[0] = nan
            pending_buy_low[0] = nan
            pending_buy_bar[0] = -1.0
            pending_sell[0] = 0.0
            pending_sell_average[0] = nan
            pending_sell_high[0] = nan
            pending_sell_bar[0] = -1.0

        report_rr_setting[0] = rr_multiplier

        # ====================================================
        # TREND CONFIRMATION
        # ====================================================

        htf_buy = self._htf_ema20[0] > self._htf_ema50[0]
        htf_sell = self._htf_ema20[0] < self._htf_ema50[0]

        bullish_trend = (
            ema20[0] > ema50[0]
            and ema50[0] > ema200[0]
        )

        bearish_trend = (
            ema20[0] < ema50[0]
            and ema50[0] < ema200[0]
        )

        buy_momentum = rsi[0] > 45
        sell_momentum = rsi[0] < 55

        # ====================================================
        # CANDLE STRUCTURE
        # ====================================================

        candle_range = self.high[0] - self.low[0]

        entry_marker_offset = max(
            candle_range * 0.25,
            abs(self.close[0]) * 0.0002
        )

        candidate_entry_price = (
            self.high[0] + self.low[0]
        ) / 2.0

        candle_body = abs(self.close[0] - self.open[0])

        lower_wick = (
            min(self.open[0], self.close[0]) - self.low[0]
        )

        upper_wick = (
            self.high[0] - max(self.open[0], self.close[0])
        )

        bullish_close_momentum = (
            candle_range > 0.0
            and self.close[0] > self.open[0]
            and (self.close[0] - self.low[0]) / candle_range >= 0.75
        )

        bearish_close_momentum = (
            candle_range > 0.0
            and self.close[0] < self.open[0]
            and (self.high[0] - self.close[0]) / candle_range >= 0.75
        )

        bullish_engulfing = (
            self.close[1] < self.open[1]
            and self.close[0] > self.open[0]
            and self.open[0] <= self.close[1]
            and self.close[0] >= self.open[1]
        )

        bearish_engulfing = (
            self.close[1] > self.open[1]
            and self.close[0] < self.open[0]
            and self.open[0] >= self.close[1]
            and self.close[0] <= self.open[1]
        )

        bullish_rejection = (
            candle_body > 0.0
            and lower_wick >= candle_body * 1.2
            and bullish_close_momentum
        )

        bearish_rejection = (
            candle_body > 0.0
            and upper_wick >= candle_body * 1.2
            and bearish_close_momentum
        )

        # ====================================================
        # PRICE ACTION PATTERNS
        # ====================================================

        bullish_hammer = (
            candle_range > 0.0
            and lower_wick >= candle_body * 2.0
            and upper_wick <= candle_body * 0.8
            and self.close[0] > self.open[0]
            and (self.close[0] - self.low[0]) / candle_range >= 0.60
        )

        bearish_shooting_star = (
            candle_range > 0.0
            and upper_wick >= candle_body * 2.0
            and lower_wick <= candle_body * 0.8
            and self.close[0] < self.open[0]
            and (self.high[0] - self.close[0]) / candle_range >= 0.60
        )

        previous_candle_range = self.high[1] - self.low[1]
        previous_candle_body = abs(self.close[1] - self.open[1])

        morning_star = (
            self.close[2] < self.open[2]
            and previous_candle_range > 0.0
            and previous_candle_body <= previous_candle_range * 0.35
            and self.close[0] > self.open[0]
            and self.close[0] > (self.open[2] + self.close[2]) / 2.0
        )

        evening_star = (
            self.close[2] > self.open[2]
            and previous_candle_range > 0.0
            and previous_candle_body <= previous_candle_range * 0.35
            and self.close[0] < self.open[0]
            and self.close[0] < (self.open[2] + self.close[2]) / 2.0
        )

        bullish_break_previous = (
            self.close[0] > self.high[1]
            and self.close[0] > self.open[0]
        )

        bearish_break_previous = (
            self.close[0] < self.low[1]
            and self.close[0] < self.open[0]
        )

        bullish_strong_body = (
            candle_range > 0.0
            and candle_body / candle_range >= 0.60
            and self.close[0] > self.open[0]
            and (self.close[0] - self.low[0]) / candle_range >= 0.70
        )

        bearish_strong_body = (
            candle_range > 0.0
            and candle_body / candle_range >= 0.60
            and self.close[0] < self.open[0]
            and (self.high[0] - self.close[0]) / candle_range >= 0.70
        )

        # ====================================================
        # 3-MINUTE CHART MULTI-TIMEFRAME CANDLE FILTER
        # ====================================================

        bullish_mtf_candle_confirm = True
        bearish_mtf_candle_confirm = True

        bullish_mtf_volume_confirm = False
        bearish_mtf_volume_confirm = False

        if self._is_3m_chart:

            bullish_mtf_volume_confirm = (
                self._m5_close[0] > self._m5_open[0]
                and self._m5_average_volume[0] > 0.0
                and self._m5_volume[0] > self._m5_average_volume[0] * 1.20
            ) or (
                self._m15_close[0] > self._m15_open[0]
                and self._m15_average_volume[0] > 0.0
                and self._m15_volume[0] > self._m15_average_volume[0] * 1.20
            )

            bearish_mtf_volume_confirm = (
                self._m5_close[0] < self._m5_open[0]
                and self._m5_average_volume[0] > 0.0
                and self._m5_volume[0] > self._m5_average_volume[0] * 1.20
            ) or (
                self._m15_close[0] < self._m15_open[0]
                and self._m15_average_volume[0] > 0.0
                and self._m15_volume[0] > self._m15_average_volume[0] * 1.20
            )

            bullish_mtf_candle_confirm = (
                self.close[0] > self.open[0]
                and (
                    self._m5_close[0] > self._m5_open[0]
                    or self._m15_close[0] > self._m15_open[0]
                    or bullish_mtf_volume_confirm
                )
            )

            bearish_mtf_candle_confirm = (
                self.close[0] < self.open[0]
                and (
                    self._m5_close[0] < self._m5_open[0]
                    or self._m15_close[0] < self._m15_open[0]
                    or bearish_mtf_volume_confirm
                )
            )

        bullish_price_action = (
            (
                bullish_engulfing
                or bullish_rejection
                or bullish_hammer
                or morning_star
                or bullish_close_momentum
                or bullish_strong_body
                or bullish_break_previous
            )
            and bullish_mtf_candle_confirm
        )

        bearish_price_action = (
            (
                bearish_engulfing
                or bearish_rejection
                or bearish_shooting_star
                or evening_star
                or bearish_close_momentum
                or bearish_strong_body
                or bearish_break_previous
            )
            and bearish_mtf_candle_confirm
        )

        # ====================================================
        # VOLUME CONFIRMATION
        # ====================================================

        average_volume = (
            self.volume[1] + self.volume[2] + self.volume[3]
            + self.volume[4] + self.volume[5] + self.volume[6]
            + self.volume[7] + self.volume[8] + self.volume[9]
            + self.volume[10]
        ) / 10.0

        volume_confirm = (
            average_volume > 0.0
            and self.volume[0] > average_volume * 1.2
        )

        buy_volume_confirm = (
            volume_confirm or bullish_mtf_volume_confirm
        )

        sell_volume_confirm = (
            volume_confirm or bearish_mtf_volume_confirm
        )

        # ====================================================
        # SUPPORT AND RESISTANCE
        # ====================================================

        support = min([
            self.low[1], self.low[2], self.low[3],
            self.low[4], self.low[5], self.low[6],
            self.low[7], self.low[8], self.low[9],
            self.low[10]
        ])

        resistance = max([
            self.high[1], self.high[2], self.high[3],
            self.high[4], self.high[5], self.high[6],
            self.high[7], self.high[8], self.high[9],
            self.high[10]
        ])

        sr_range = resistance - support

        support_zone = (
            sr_range > 0.0
            and self.low[0] <= support + sr_range * 0.15
            and self.close[0] > support
        )

        resistance_zone = (
            sr_range > 0.0
            and self.high[0] >= resistance - sr_range * 0.15
            and self.close[0] < resistance
        )

        # ====================================================
        # BREAKOUT + VOLUME SETUPS - BOTH DIRECTIONS
        # ====================================================

        bullish_breakout_volume_setup = (
            self.close[0] > resistance
            and self.close[0] > self.open[0]
            and volume_confirm
            and (
                bullish_strong_body
                or bullish_close_momentum
            )
        )

        bearish_breakout_volume_setup = (
            self.close[0] < support
            and self.close[0] < self.open[0]
            and volume_confirm
            and (
                bearish_strong_body
                or bearish_close_momentum
            )
        )

        # ====================================================
        # EMA PULLBACK
        # ====================================================

        buy_pullback = (
            self.low[0] <= ema20[0]
            and self.close[0] > ema9[0]
            and self.close[0] > self.open[0]
        )

        sell_pullback = (
            self.high[0] >= ema20[0]
            and self.close[0] < ema9[0]
            and self.close[0] < self.open[0]
        )

        # ====================================================
        # SUPPORT / RESISTANCE REJECTION
        # ====================================================

        buy_rejection_setup = (
            support_zone
            and buy_volume_confirm
            and (bullish_engulfing or bullish_rejection)
        )

        sell_rejection_setup = (
            resistance_zone
            and sell_volume_confirm
            and (bearish_engulfing or bearish_rejection)
        )

        # ====================================================
        # LOCAL BULLISH ORDER BLOCK
        # ====================================================

        bullish_ob_low = nan
        bullish_ob_high = nan

        if self.close[1] < self.open[1]:
            bullish_ob_low = self.low[1]
            bullish_ob_high = self.high[1]
        elif self.close[2] < self.open[2]:
            bullish_ob_low = self.low[2]
            bullish_ob_high = self.high[2]
        elif self.close[3] < self.open[3]:
            bullish_ob_low = self.low[3]
            bullish_ob_high = self.high[3]
        elif self.close[4] < self.open[4]:
            bullish_ob_low = self.low[4]
            bullish_ob_high = self.high[4]
        elif self.close[5] < self.open[5]:
            bullish_ob_low = self.low[5]
            bullish_ob_high = self.high[5]

        bullish_ob_touch = (
            bullish_ob_low == bullish_ob_low
            and self.low[0] <= bullish_ob_high
            and self.high[0] >= bullish_ob_low
            and self.close[0] > bullish_ob_low
            and self.close[0] > self.open[0]
            and bullish_mtf_candle_confirm
        )

        # ====================================================
        # LOCAL BEARISH ORDER BLOCK
        # ====================================================

        bearish_ob_low = nan
        bearish_ob_high = nan

        if self.close[1] > self.open[1]:
            bearish_ob_low = self.low[1]
            bearish_ob_high = self.high[1]
        elif self.close[2] > self.open[2]:
            bearish_ob_low = self.low[2]
            bearish_ob_high = self.high[2]
        elif self.close[3] > self.open[3]:
            bearish_ob_low = self.low[3]
            bearish_ob_high = self.high[3]
        elif self.close[4] > self.open[4]:
            bearish_ob_low = self.low[4]
            bearish_ob_high = self.high[4]
        elif self.close[5] > self.open[5]:
            bearish_ob_low = self.low[5]
            bearish_ob_high = self.high[5]

        bearish_ob_touch = (
            bearish_ob_low == bearish_ob_low
            and self.low[0] <= bearish_ob_high
            and self.high[0] >= bearish_ob_low
            and self.close[0] < bearish_ob_high
            and self.close[0] < self.open[0]
            and bearish_mtf_candle_confirm
        )

        # ====================================================
        # FAIR VALUE GAP
        # ====================================================

        bullish_fvg_valid = self.low[1] > self.high[3]

        bullish_fvg_low = self.high[3]
        bullish_fvg_high = self.low[1]

        bullish_fvg_touch = (
            bullish_fvg_valid
            and self.low[0] <= bullish_fvg_high
            and self.high[0] >= bullish_fvg_low
            and self.close[0] > bullish_fvg_low
            and self.close[0] > self.open[0]
        )

        bearish_fvg_valid = self.high[1] < self.low[3]

        bearish_fvg_low = self.high[1]
        bearish_fvg_high = self.low[3]

        bearish_fvg_touch = (
            bearish_fvg_valid
            and self.high[0] >= bearish_fvg_low
            and self.low[0] <= bearish_fvg_high
            and self.close[0] < bearish_fvg_high
            and self.close[0] < self.open[0]
        )

        # ====================================================
        # HEAD AND SHOULDERS
        # ====================================================

        hs_left_shoulder = self.high[8]
        hs_head = self.high[5]
        hs_right_shoulder = self.high[2]

        hs_neckline = (self.low[7] + self.low[3]) / 2.0

        hs_shoulders_similar = (
            sr_range > 0.0
            and abs(hs_left_shoulder - hs_right_shoulder) <= sr_range * 0.15
        )

        head_shoulders_sell = (
            hs_shoulders_similar
            and hs_head > hs_left_shoulder
            and hs_head > hs_right_shoulder
            and self.close[0] < hs_neckline
            and self.close[0] < self.open[0]
        )

        # ====================================================
        # INVERSE HEAD AND SHOULDERS
        # ====================================================

        ihs_left_shoulder = self.low[8]
        ihs_head = self.low[5]
        ihs_right_shoulder = self.low[2]

        ihs_neckline = (self.high[7] + self.high[3]) / 2.0

        ihs_shoulders_similar = (
            sr_range > 0.0
            and abs(ihs_left_shoulder - ihs_right_shoulder) <= sr_range * 0.15
        )

        inverse_head_shoulders_buy = (
            ihs_shoulders_similar
            and ihs_head < ihs_left_shoulder
            and ihs_head < ihs_right_shoulder
            and self.close[0] > ihs_neckline
            and self.close[0] > self.open[0]
        )

        # ====================================================
        # EXISTING SETUPS
        # ====================================================

        buy_existing_setup = (
            buy_pullback
            and (
                bullish_ob_touch
                or bullish_fvg_touch
                or support_zone
            )
        )

        sell_existing_setup = (
            sell_pullback
            and (
                bearish_ob_touch
                or bearish_fvg_touch
                or resistance_zone
            )
        )

        # ====================================================
        # EXISTING VOLUME IMPULSE SETUP
        # ====================================================

        bullish_volume_impulse_setup = (
            self._is_3m_chart
            and bullish_price_action
            and buy_momentum
            and buy_volume_confirm
            and (
                bullish_close_momentum
                or bullish_strong_body
                or bullish_break_previous
                or bullish_engulfing
            )
        )

        bearish_volume_impulse_setup = (
            self._is_3m_chart
            and bearish_price_action
            and sell_momentum
            and sell_volume_confirm
            and (
                bearish_close_momentum
                or bearish_strong_body
                or bearish_break_previous
                or bearish_engulfing
            )
        )

        # ====================================================
        # FINAL BUY / SELL CONDITIONS
        # ====================================================

        buy_condition = (
            (
                htf_buy
                and bullish_trend
                and buy_momentum
                and bullish_price_action
                and (
                    buy_existing_setup
                    or buy_rejection_setup
                    or bullish_ob_touch
                    or bullish_fvg_touch
                    or inverse_head_shoulders_buy
                )
            )
            or bullish_volume_impulse_setup
        )

        sell_condition = (
            (
                htf_sell
                and bearish_trend
                and sell_momentum
                and bearish_price_action
                and (
                    sell_existing_setup
                    or sell_rejection_setup
                    or bearish_ob_touch
                    or bearish_fvg_touch
                    or head_shoulders_sell
                )
            )
            or bearish_volume_impulse_setup
        )

        # ====================================================
        # ADD-ON ENTRY SCORES
        # ====================================================

        buy_add_score = 0

        if bullish_engulfing or bullish_close_momentum:
            buy_add_score += 2

        if bullish_rejection or bullish_hammer:
            buy_add_score += 2

        if morning_star or bullish_break_previous:
            buy_add_score += 2

        if support_zone:
            buy_add_score += 2

        if bullish_ob_touch or bullish_fvg_touch:
            buy_add_score += 2

        if self.close[0] > ema9[0] and self.close[0] > ema20[0]:
            buy_add_score += 1

        if rsi[0] > rsi[1] and rsi[0] > 40:
            buy_add_score += 1

        buy_add_location = (
            support_zone
            or bullish_ob_touch
            or bullish_fvg_touch
        )

        sell_add_score = 0

        if bearish_engulfing or bearish_close_momentum:
            sell_add_score += 2

        if bearish_rejection or bearish_shooting_star:
            sell_add_score += 2

        if evening_star or bearish_break_previous:
            sell_add_score += 2

        if resistance_zone:
            sell_add_score += 2

        if bearish_ob_touch or bearish_fvg_touch:
            sell_add_score += 2

        if self.close[0] < ema9[0] and self.close[0] < ema20[0]:
            sell_add_score += 1

        if rsi[0] < rsi[1] and rsi[0] < 60:
            sell_add_score += 1

        sell_add_location = (
            resistance_zone
            or bearish_ob_touch
            or bearish_fvg_touch
        )

        # ====================================================
        # BUY / SELL REASONS
        # ====================================================

        buy_reason = ''
        sell_reason = ''

        if bullish_breakout_volume_setup:
            buy_reason = 'BREAKOUT + VOLUME'

        elif bullish_ob_touch:
            buy_reason = 'OB'

        if not bullish_breakout_volume_setup:

            if bullish_fvg_touch:
                if buy_reason != '':
                    buy_reason += ' + FVG'
                else:
                    buy_reason = 'FVG'

            if buy_rejection_setup:
                if buy_reason != '':
                    buy_reason += ' + Support'
                else:
                    buy_reason = 'S'

            if inverse_head_shoulders_buy:
                if buy_reason != '':
                    buy_reason += ' + Inv H&S'
                else:
                    buy_reason = 'Inv H&S'

            if buy_pullback:
                if buy_reason != '':
                    buy_reason += ' + EMA Pullback'
                else:
                    buy_reason = 'EMA'

            if bullish_price_action:
                if buy_reason != '':
                    buy_reason += ' + Price Action'
                else:
                    buy_reason = 'PA'

            if bullish_trend and htf_buy:
                if buy_reason != '':
                    buy_reason += ' + HTF Trend'
                else:
                    buy_reason = 'HTF'

            if buy_momentum:
                if buy_reason != '':
                    buy_reason += ' + RSI'
                else:
                    buy_reason = 'RSI'

            if buy_volume_confirm and (
                buy_rejection_setup or bullish_volume_impulse_setup
            ):
                buy_reason += ' + Volume'

        if bearish_breakout_volume_setup:
            sell_reason = 'BREAKOUT + VOLUME'

        elif bearish_ob_touch:
            sell_reason = 'OB'

        if not bearish_breakout_volume_setup:

            if bearish_fvg_touch:
                if sell_reason != '':
                    sell_reason += ' + FVG'
                else:
                    sell_reason = 'FVG'

            if sell_rejection_setup:
                if sell_reason != '':
                    sell_reason += ' + Resistance'
                else:
                    sell_reason = 'R'

            if head_shoulders_sell:
                if sell_reason != '':
                    sell_reason += ' + H&S'
                else:
                    sell_reason = 'H&S'

            if sell_pullback:
                if sell_reason != '':
                    sell_reason += ' + EMA Pullback'
                else:
                    sell_reason = 'EMA'

            if bearish_price_action:
                if sell_reason != '':
                    sell_reason += ' + Price Action'
                else:
                    sell_reason = 'PA'

            if bearish_trend and htf_sell:
                if sell_reason != '':
                    sell_reason += ' + HTF Trend'
                else:
                    sell_reason = 'HTF'

            if sell_momentum:
                if sell_reason != '':
                    sell_reason += ' + RSI'
                else:
                    sell_reason = 'RSI'

            if sell_volume_confirm and (
                sell_rejection_setup or bearish_volume_impulse_setup
            ):
                sell_reason += ' + Volume'

        if buy_reason == '':
            buy_reason = 'Trend+RSI'

        if sell_reason == '':
            sell_reason = 'Trend+RSI'

        # ====================================================
        # TRADE MANAGEMENT
        # ====================================================

        buy_signal = False
        sell_signal = False
        trade_exited = False

        current_ist_day_key = float(int((self.time[0] + 19800.0) // 86400.0))
        report_hit_sl = False
        report_hit_tp = False
        report_hit_trailing_sl = False

        # Reset the daily baseline at 12:00 AM IST (one epoch-day key per IST day).
        # account_capital is the configured starting-balance snapshot for the day.
        if risk_day_key[0] != current_ist_day_key:
            risk_day_key[0] = current_ist_day_key
            daily_start_balance[0] = self.account_capital
            daily_realized_pnl[0] = 0.0
            reduced_risk_mode[0] = 0.0

        # Midpoint-first pending lifecycle. No active trade exists until midpoint fills.
        if (
            self.is_closed_bar
            and pending_trade_side[0] != 0.0
            and self.bar_index > pending_trade_setup_bar[0]
            and side[0] == 0.0
        ):
            pending_side_value = pending_trade_side[0]
            pending_mid_value = pending_trade_entry[0]
            pending_sl_value = pending_trade_sl[0]
            pending_tp_value = pending_trade_tp[0]
            pending_mid_lot_value = pending_trade_lot[0]
            pending_budget_value = setup_risk_budget[0]

            midpoint_touched = (
                self.low[0] <= pending_mid_value
                if pending_side_value == 1.0 else
                self.high[0] >= pending_mid_value
            )
            pending_sl_touched = (
                self.low[0] <= pending_sl_value
                if pending_side_value == 1.0 else
                self.high[0] >= pending_sl_value
            )
            pending_tp_touched = (
                self.high[0] >= pending_tp_value
                if pending_side_value == 1.0 else
                self.low[0] <= pending_tp_value
            )

            # Conservative candle simulation: SL/TP takes priority over midpoint
            # when both are touched in the same completed candle.
            if pending_sl_touched or pending_tp_touched:
                inactive_result = 0.0
                if pending_sl_touched:
                    inactive_result = (
                        -abs(pending_mid_value - pending_sl_value)
                        * self.contract_size * pending_mid_lot_value
                    )
                elif pending_tp_touched:
                    inactive_result = (
                        abs(pending_tp_value - pending_mid_value)
                        * self.contract_size * pending_mid_lot_value
                    )

                if pending_trade_setup_day[0] == self._selected_report_day_key:
                    report_inactive_pnl[0] = report_inactive_pnl[0] + inactive_result

                pending_trade_side[0] = 0.0
                pending_trade_entry[0] = nan
                pending_trade_sl[0] = nan
                pending_trade_tp[0] = nan
                pending_trade_lot[0] = nan
                pending_trade_risk_cash[0] = nan
                pending_trade_setup_day[0] = nan
                pending_trade_setup_bar[0] = -1.0
                pending_mid_entry[0] = nan
                setup_risk_budget[0] = nan

            elif midpoint_touched:
                # Midpoint fills first. The second leg is simulated at the
                # close of this completed candle, not as a broker execution.
                midpoint_distance = abs(pending_mid_value - pending_sl_value)
                midpoint_risk_cash = (
                    pending_mid_lot_value * midpoint_distance * self.contract_size
                )
                remaining_risk_cash = max(0.0, pending_budget_value - midpoint_risk_cash)
                immediate_price = self.close[0]
                immediate_distance = abs(immediate_price - pending_sl_value)
                immediate_lot = 0.0

                if (
                    immediate_distance > 0.0
                    and (
                        (pending_side_value == 1.0 and immediate_price > pending_sl_value)
                        or (pending_side_value == -1.0 and immediate_price < pending_sl_value)
                    )
                ):
                    immediate_risk_per_lot = immediate_distance * self.contract_size
                    if immediate_risk_per_lot > 0.0:
                        raw_immediate_lot = remaining_risk_cash / immediate_risk_per_lot
                        immediate_lot = int(raw_immediate_lot * 100.0) / 100.0

                        # Preserve the original full-budget midpoint lot as a
                        # hard total-lot ceiling, in addition to the dollar cap.
                        midpoint_total_lot_cap = (
                            int((pending_budget_value / (midpoint_distance * self.contract_size)) * 100.0) / 100.0
                            if midpoint_distance > 0.0 else 0.0
                        )
                        remaining_lot_cap = max(0.0, midpoint_total_lot_cap - pending_mid_lot_value)
                        immediate_lot = min(immediate_lot, remaining_lot_cap)

                        # Recheck combined risk after rounding down to 0.01 lots.
                        combined_risk = (
                            midpoint_risk_cash
                            + immediate_lot * immediate_distance * self.contract_size
                        )
                        while immediate_lot >= 0.01 and combined_risk > pending_budget_value:
                            immediate_lot = int((immediate_lot - 0.01) * 100.0) / 100.0
                            combined_risk = (
                                midpoint_risk_cash
                                + immediate_lot * immediate_distance * self.contract_size
                            )

                if immediate_lot < 0.01:
                    immediate_lot = 0.0

                entry[0] = pending_mid_value
                midpoint_master_entry[0] = pending_mid_value
                mid_leg_lot[0] = pending_mid_lot_value
                mid_leg_active[0] = 1.0

                # Keep the immediate leg at zero size when the remaining
                # risk cannot support the minimum 0.01 lot.
                early_leg_entry[0] = immediate_price if immediate_lot >= 0.01 else pending_mid_value
                early_leg_lot[0] = immediate_lot
                early_leg_closed[0] = 0.0
                early_leg_pnl[0] = 0.0
                mid_leg_pnl[0] = 0.0

                side[0] = pending_side_value
                sl[0] = pending_sl_value
                tp[0] = pending_tp_value
                trade_lot[0] = pending_mid_lot_value + immediate_lot
                trade_risk_cash[0] = (
                    midpoint_risk_cash
                    + immediate_lot * immediate_distance * self.contract_size
                )
                original_risk_distance[0] = midpoint_distance
                favorable_extreme[0] = pending_mid_value
                trail_candidate[0] = nan
                trail_confirm_count[0] = 0.0
                trail_stage[0] = 0.0
                trail_last_update_bar[0] = -1.0
                early_exit_warned[0] = 0.0
                entry_count[0] = 2.0 if immediate_lot >= 0.01 else 1.0
                last_entry_bar[0] = float(self.bar_index)
                last_entry_price[0] = pending_mid_value
                entry_label_time[0] = self.time[0]
                pending_early_entry[0] = immediate_price if immediate_lot >= 0.01 else nan

                # Compact entry tags keep the chart readable.
                self.chart.draw(LabelAbs(
                    'MID ' + str(round(pending_mid_lot_value, 2)),
                    AbsolutePosition(self.time[0], pending_mid_value),
                    font_size=8, text_color=color.BLACK,
                    bg_color=color.TRANSPARENT
                ))
                if immediate_lot >= 0.01:
                    self.chart.draw(LabelAbs(
                        'ADD ' + str(round(immediate_lot, 2)),
                        AbsolutePosition(self.time[0], immediate_price),
                        font_size=8, text_color=color.BLACK,
                        bg_color=color.TRANSPARENT
                    ))

                pending_trade_side[0] = 0.0
                pending_trade_entry[0] = nan
                pending_trade_sl[0] = nan
                pending_trade_tp[0] = nan
                pending_trade_lot[0] = nan
                pending_trade_risk_cash[0] = nan
                pending_trade_setup_day[0] = nan
                pending_trade_setup_bar[0] = -1.0
                pending_mid_entry[0] = nan


        if self.is_closed_bar:

            # Setup-counter candidates are declared inside the closed-bar parent
            # block so nested tracker conditions can resolve them in Indie.
            count_new_side = 0.0
            count_new_entry = nan
            count_new_stop = nan
            count_new_tp = nan
            count_new_risk = 0.0
            count_new_distance = 0.0
            count_new_risk_per_lot = 0.0
            count_new_lot = 0.0

            pass
            # ================================================
            # EXITS
            # ================================================

            exit_now = False
            manual_exit_now = (
                side[0] != 0.0
                and self.manual_exit_bar_index >= 0
                and self.bar_index == self.manual_exit_bar_index
            )
            if manual_exit_now:
                exit_now = True
            elif side[0] == 1.0:
                report_hit_sl = self.low[0] <= sl[0]
                report_hit_tp = self.high[0] >= tp[0]
                exit_now = report_hit_sl or report_hit_tp
            elif side[0] == -1.0:
                report_hit_sl = self.high[0] >= sl[0]
                report_hit_tp = self.low[0] <= tp[0]
                exit_now = report_hit_sl or report_hit_tp

            report_hit_trailing_sl = report_hit_sl and trail_last_update_bar[0] >= 0.0

            if exit_now:
                if report_hit_sl or report_hit_tp:
                    realized_exit_price = sl[0] if report_hit_sl else tp[0]
                    early_leg_result = (
                        (realized_exit_price - early_leg_entry[0])
                        * side[0] * self.contract_size * early_leg_lot[0]
                        if early_leg_closed[0] == 0.0 else 0.0
                    )
                    mid_leg_result = (
                        (realized_exit_price - midpoint_master_entry[0])
                        * side[0] * self.contract_size * mid_leg_lot[0]
                        if mid_leg_active[0] == 1.0 else 0.0
                    )
                    realized_pnl = early_leg_result + mid_leg_result
                    result_amount = abs(realized_pnl)

                    if report_hit_tp and not report_hit_sl:
                        self.chart.draw(LabelAbs(
                            'TP +

                    if current_ist_day_key == risk_day_key[0]:
                        daily_realized_pnl[0] = daily_realized_pnl[0] + realized_pnl
                        daily_loss_threshold = daily_start_balance[0] * 0.30
                        if daily_realized_pnl[0] <= -daily_loss_threshold:
                            reduced_risk_mode[0] = 1.0
                        elif daily_realized_pnl[0] >= 0.0:
                            reduced_risk_mode[0] = 0.0

                    if current_ist_day_key == self._selected_report_day_key:
                        if report_hit_trailing_sl:
                            report_trailing_sl[0] = report_trailing_sl[0] + 1.0
                        elif report_hit_sl:
                            report_sl[0] = report_sl[0] + 1.0
                        elif report_hit_tp:
                            report_tp[0] = report_tp[0] + 1.0
                        report_net_profit[0] = report_net_profit[0] + realized_pnl
                        report_active_pnl[0] = report_active_pnl[0] + realized_pnl

                    if (
                        current_ist_day_key >= self._selected_report_month_start_key
                        and current_ist_day_key < self._selected_report_month_end_key
                    ):
                        monthly_net_profit[0] = monthly_net_profit[0] + realized_pnl
                    if current_ist_day_key == self._selected_report_month_start_key + 0.0:
                        monthly_day_01_profit[0] = monthly_day_01_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 1.0:
                        monthly_day_02_profit[0] = monthly_day_02_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 2.0:
                        monthly_day_03_profit[0] = monthly_day_03_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 3.0:
                        monthly_day_04_profit[0] = monthly_day_04_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 4.0:
                        monthly_day_05_profit[0] = monthly_day_05_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 5.0:
                        monthly_day_06_profit[0] = monthly_day_06_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 6.0:
                        monthly_day_07_profit[0] = monthly_day_07_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 7.0:
                        monthly_day_08_profit[0] = monthly_day_08_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 8.0:
                        monthly_day_09_profit[0] = monthly_day_09_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 9.0:
                        monthly_day_10_profit[0] = monthly_day_10_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 10.0:
                        monthly_day_11_profit[0] = monthly_day_11_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 11.0:
                        monthly_day_12_profit[0] = monthly_day_12_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 12.0:
                        monthly_day_13_profit[0] = monthly_day_13_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 13.0:
                        monthly_day_14_profit[0] = monthly_day_14_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 14.0:
                        monthly_day_15_profit[0] = monthly_day_15_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 15.0:
                        monthly_day_16_profit[0] = monthly_day_16_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 16.0:
                        monthly_day_17_profit[0] = monthly_day_17_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 17.0:
                        monthly_day_18_profit[0] = monthly_day_18_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 18.0:
                        monthly_day_19_profit[0] = monthly_day_19_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 19.0:
                        monthly_day_20_profit[0] = monthly_day_20_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 20.0:
                        monthly_day_21_profit[0] = monthly_day_21_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 21.0:
                        monthly_day_22_profit[0] = monthly_day_22_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 22.0:
                        monthly_day_23_profit[0] = monthly_day_23_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 23.0:
                        monthly_day_24_profit[0] = monthly_day_24_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 24.0:
                        monthly_day_25_profit[0] = monthly_day_25_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 25.0:
                        monthly_day_26_profit[0] = monthly_day_26_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 26.0:
                        monthly_day_27_profit[0] = monthly_day_27_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 27.0:
                        monthly_day_28_profit[0] = monthly_day_28_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 28.0:
                        monthly_day_29_profit[0] = monthly_day_29_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 29.0:
                        monthly_day_30_profit[0] = monthly_day_30_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 30.0:
                        monthly_day_31_profit[0] = monthly_day_31_profit[0] + realized_pnl

                entry[0] = nan
                early_leg_entry[0] = nan
                midpoint_master_entry[0] = nan
                early_leg_lot[0] = nan
                mid_leg_lot[0] = nan
                mid_leg_active[0] = 0.0
                early_leg_closed[0] = 0.0
                pending_mid_entry[0] = nan
                pending_early_entry[0] = nan
                pending_trade_side[0] = 0.0
                pending_trade_entry[0] = nan
                pending_trade_sl[0] = nan
                pending_trade_tp[0] = nan
                pending_trade_lot[0] = nan
                pending_trade_risk_cash[0] = nan
                pending_trade_setup_day[0] = nan
                pending_trade_setup_bar[0] = -1.0
                second_entry_price[0] = nan
                third_entry_price[0] = nan
                fourth_entry_price[0] = nan
                fifth_entry_price[0] = nan
                sl[0] = nan
                tp[0] = nan
                side[0] = 0.0
                trade_lot[0] = nan
                trade_risk_cash[0] = nan
                original_risk_distance[0] = nan
                favorable_extreme[0] = nan
                trail_candidate[0] = nan
                trail_confirm_count[0] = 0.0
                trail_stage[0] = 0.0
                trail_last_update_bar[0] = -1.0
                entry_count[0] = 0.0
                last_entry_bar[0] = -1.0
                last_entry_price[0] = nan
                entry_label_time[0] = nan
                early_exit_warned[0] = 0.0
                pending_buy[0] = 0.0
                pending_buy_average[0] = nan
                pending_buy_low[0] = nan
                pending_buy_bar[0] = -1.0
                pending_sell[0] = 0.0
                pending_sell_average[0] = nan
                pending_sell_high[0] = nan
                pending_sell_bar[0] = -1.0
                trade_exited = True

            # ================================================
            # ADAPTIVE HYBRID TRAILING (M1, CLOSED CANDLES ONLY)
            # ================================================
            # This is a chart-side simulated stop line. Exness Indie custom
            # indicators cannot modify an actual broker position's SL.
            if (
                self.adaptive_trailing_enabled
                and self._is_m1_chart
                and side[0] != 0.0
                and mid_leg_active[0] == 1.0
                and self.bar_index > last_entry_bar[0]
                and original_risk_distance[0] > 0.0
                and not trade_exited
            ):
                is_buy_trail = side[0] == 1.0
                entry[0] = midpoint_master_entry[0]
                risk_unit = original_risk_distance[0]
                atr_value = atr14[0]
                adx_value = adx14[0]
                minus_value = minus_di[0]
                plus_value = plus_di[0]
                proposed_sl = sl[0]

                # Track the best favourable excursion since the simulated entry.
                # Declare shared-scope values before the BUY/SELL branches.
                favourable_move = 0.0
                target_distance = 0.0
                if is_buy_trail:
                    if isnan(favorable_extreme[0]):
                        favorable_extreme[0] = self.high[0]
                    else:
                        favorable_extreme[0] = max(favorable_extreme[0], self.high[0])
                    favourable_move = favorable_extreme[0] - entry[0]
                    target_distance = tp[0] - entry[0]
                else:
                    if isnan(favorable_extreme[0]):
                        favorable_extreme[0] = self.low[0]
                    else:
                        favorable_extreme[0] = min(favorable_extreme[0], self.low[0])
                    favourable_move = entry[0] - favorable_extreme[0]
                    target_distance = entry[0] - tp[0]

                r_progress = favourable_move / risk_unit if risk_unit > 0.0 else 0.0
                tp_progress = (
                    favourable_move / target_distance
                    if target_distance > 0.0 else 0.0
                )

                # 1R: break-even (optional user-supplied cost buffer).
                if r_progress >= 1.0:
                    if is_buy_trail:
                        proposed_sl = max(proposed_sl, entry[0] + self.break_even_buffer)
                    else:
                        proposed_sl = min(proposed_sl, entry[0] - self.break_even_buffer)

                # TP progress locks are based on the ORIGINAL risk distance.
                if tp_progress >= 0.95:
                    lock_price = 0.60 * risk_unit
                    if is_buy_trail:
                        proposed_sl = max(proposed_sl, entry[0] + lock_price)
                    else:
                        proposed_sl = min(proposed_sl, entry[0] - lock_price)
                elif tp_progress >= 0.85:
                    lock_price = 0.30 * risk_unit
                    if is_buy_trail:
                        proposed_sl = max(proposed_sl, entry[0] + lock_price)
                    else:
                        proposed_sl = min(proposed_sl, entry[0] - lock_price)

                # Swing structure + ATR trailing begins after 1.4R.
                if r_progress >= 1.4 and not isnan(atr_value) and atr_value > 0.0:
                    strong_buy_trend = (
                        adx_value >= 25.0
                        and plus_value > minus_value
                        and trail_ema9[0] > trail_ema21[0]
                    )
                    strong_sell_trend = (
                        adx_value >= 25.0
                        and minus_value > plus_value
                        and trail_ema9[0] < trail_ema21[0]
                    )
                    atr_multiplier = 1.5 if (
                        (is_buy_trail and strong_buy_trend)
                        or ((not is_buy_trail) and strong_sell_trend)
                    ) else 1.0
                    atr_buffer = atr_value * atr_multiplier

                    if is_buy_trail:
                        # Confirmed pivot low: two bars on either side.
                        confirmed_swing_low = (
                            self.low[2] < self.low[1]
                            and self.low[2] < self.low[0]
                            and self.low[2] <= self.low[3]
                            and self.low[2] <= self.low[4]
                        )
                        if confirmed_swing_low:
                            swing_candidate = self.low[2] - atr_buffer
                            if swing_candidate > proposed_sl and swing_candidate < self.close[0]:
                                proposed_sl = max(proposed_sl, swing_candidate)

                        # Three bearish closes are a confirmed adverse reaction.
                        bearish_three = (
                            self.close[0] < self.close[1]
                            and self.close[1] < self.close[2]
                            and self.close[0] < trail_ema9[0]
                        )
                        if bearish_three:
                            reaction_candidate = min([
                                self.low[0], self.low[1], self.low[2]
                            ]) - atr_value
                            if reaction_candidate > proposed_sl and reaction_candidate < self.close[0]:
                                proposed_sl = max(proposed_sl, reaction_candidate)
                    else:
                        # Confirmed pivot high: two bars on either side.
                        confirmed_swing_high = (
                            self.high[2] > self.high[1]
                            and self.high[2] > self.high[0]
                            and self.high[2] >= self.high[3]
                            and self.high[2] >= self.high[4]
                        )
                        if confirmed_swing_high:
                            swing_candidate = self.high[2] + atr_buffer
                            if swing_candidate < proposed_sl and swing_candidate > self.close[0]:
                                proposed_sl = min(proposed_sl, swing_candidate)

                        # Three bullish closes are a confirmed adverse reaction.
                        bullish_three = (
                            self.close[0] > self.close[1]
                            and self.close[1] > self.close[2]
                            and self.close[0] > trail_ema9[0]
                        )
                        if bullish_three:
                            reaction_candidate = max([
                                self.high[0], self.high[1], self.high[2]
                            ]) + atr_value
                            if reaction_candidate < proposed_sl and reaction_candidate > self.close[0]:
                                proposed_sl = min(proposed_sl, reaction_candidate)

                # Candidate must improve protection and remain beyond the close.
                candidate_is_valid = (
                    proposed_sl > sl[0] and proposed_sl < self.close[0]
                    if is_buy_trail else
                    proposed_sl < sl[0] and proposed_sl > self.close[0]
                )

                # Require 3 consecutive completed M1 closes to confirm the same
                # or a more protective candidate. Never loosen an existing stop.
                if candidate_is_valid:
                    if is_buy_trail:
                        if isnan(trail_candidate[0]) or proposed_sl > trail_candidate[0]:
                            trail_candidate[0] = proposed_sl
                            trail_confirm_count[0] = 0.0
                    else:
                        if isnan(trail_candidate[0]) or proposed_sl < trail_candidate[0]:
                            trail_candidate[0] = proposed_sl
                            trail_confirm_count[0] = 0.0

                if not isnan(trail_candidate[0]):
                    candidate_still_safe = (
                        self.close[0] > trail_candidate[0]
                        if is_buy_trail else
                        self.close[0] < trail_candidate[0]
                    )
                    if candidate_still_safe:
                        trail_confirm_count[0] = trail_confirm_count[0] + 1.0
                    else:
                        trail_candidate[0] = nan
                        trail_confirm_count[0] = 0.0

                if (
                    not isnan(trail_candidate[0])
                    and trail_confirm_count[0] >= 3.0
                    and (
                        (is_buy_trail and trail_candidate[0] > sl[0])
                        or ((not is_buy_trail) and trail_candidate[0] < sl[0])
                    )
                ):
                    sl[0] = trail_candidate[0]
                    trail_last_update_bar[0] = float(self.bar_index)
                    trail_confirm_count[0] = 0.0
                    trail_candidate[0] = nan

                    # Keep the chart uncluttered: the SL line itself shows
                    # every trailing adjustment; do not add repeated text labels.
                    if tp_progress >= 0.95:
                        trail_stage[0] = 3.0
                    elif tp_progress >= 0.85:
                        trail_stage[0] = 2.0
                    elif r_progress >= 1.0:
                        trail_stage[0] = 1.0
                    else:
                        trail_stage[0] = 4.0

                entry[0] = early_leg_entry[0]

            # ================================================
            # EARLY EXIT WARNING
            # ================================================

            if side[0] == 1.0 and early_exit_warned[0] == 0.0:

                buy_failure_score = 0

                if self.close[0] < ema20[0] and ema20[0] < ema50[0]:
                    buy_failure_score += 1

                if htf_sell:
                    buy_failure_score += 1

                if rsi[0] < 45 and rsi[0] < rsi[1]:
                    buy_failure_score += 1

                if bearish_price_action:
                    buy_failure_score += 1

                if buy_failure_score >= 3:

                    early_exit_warned[0] = 1.0

                    if self.is_closed_bar:

                        pass

            elif side[0] == -1.0 and early_exit_warned[0] == 0.0:

                sell_failure_score = 0

                if self.close[0] > ema20[0] and ema20[0] > ema50[0]:
                    sell_failure_score += 1

                if htf_buy:
                    sell_failure_score += 1

                if rsi[0] > 55 and rsi[0] > rsi[1]:
                    sell_failure_score += 1

                if bullish_price_action:
                    sell_failure_score += 1

                if sell_failure_score >= 3:

                    early_exit_warned[0] = 1.0

                    if self.is_closed_bar:

                        pass

            # ================================================
            # ADD-ON ENTRIES 2 TO 5
            # ================================================

            if (
                side[0] != 0.0
                and entry_count[0] >= 1.0
                and entry_count[0] < 5.0
                and self.bar_index > last_entry_bar[0]
            ):

                is_buy_side = side[0] == 1.0

                add_ok = False

                if is_buy_side:

                    add_ok = (
                        candidate_entry_price < last_entry_price[0]
                        and bullish_price_action
                        and buy_add_location
                        and buy_add_score >= 4
                    )

                else:

                    add_ok = (
                        candidate_entry_price > last_entry_price[0]
                        and bearish_price_action
                        and sell_add_location
                        and sell_add_score >= 4
                    )

                if add_ok:

                    new_count = entry_count[0] + 1.0

                    entry_count[0] = new_count
                    last_entry_bar[0] = float(self.bar_index)
                    last_entry_price[0] = candidate_entry_price

                    add_name = 'Second'
                    add_color = color.BLACK

                    if new_count == 2.0:
                        second_entry_price[0] = candidate_entry_price

                    elif new_count == 3.0:
                        third_entry_price[0] = candidate_entry_price
                        add_name = 'Third'
                        add_color = color.FUCHSIA

                    elif new_count == 4.0:
                        fourth_entry_price[0] = candidate_entry_price
                        add_name = 'Fourth'
                        add_color = color.YELLOW

                    else:
                        fifth_entry_price[0] = candidate_entry_price
                        add_name = 'Fifth'
                        add_color = color.PURPLE

                    add_setup_name = add_name + (
                        ' BUY' if is_buy_side else ' SELL'
                    )

                    if not (
                        self.delete_setup == add_setup_name
                        and self.bar_index == self.delete_bar_index
                    ):

                        if is_buy_side:

                            if self.is_closed_bar:

                                pass

                        else:

                            if self.is_closed_bar:

                                pass

            # ================================================
            # ARM NEW BREAKOUT PULLBACK SETUPS
            # ================================================

            if side[0] == 0.0 and not trade_exited:

                if bullish_breakout_volume_setup:

                    pending_buy[0] = 1.0
                    pending_buy_average[0] = (
                        self.high[0] + self.low[0]
                    ) / 2.0
                    pending_buy_low[0] = self.low[0]
                    pending_buy_bar[0] = float(self.bar_index)

                    pending_sell[0] = 0.0
                    pending_sell_average[0] = nan
                    pending_sell_high[0] = nan
                    pending_sell_bar[0] = -1.0

                elif bearish_breakout_volume_setup:

                    pending_sell[0] = 1.0
                    pending_sell_average[0] = (
                        self.high[0] + self.low[0]
                    ) / 2.0
                    pending_sell_high[0] = self.high[0]
                    pending_sell_bar[0] = float(self.bar_index)

                    pending_buy[0] = 0.0
                    pending_buy_average[0] = nan
                    pending_buy_low[0] = nan
                    pending_buy_bar[0] = -1.0

            # ================================================
            # VALIDATE / EXPIRE PENDING BUY SETUP
            # ================================================

            if (
                pending_buy[0] == 1.0
                and self.bar_index > pending_buy_bar[0]
            ):

                buy_pending_age = (
                    self.bar_index - pending_buy_bar[0]
                )

                if (
                    buy_pending_age > 10.0
                    or self.close[0] < pending_buy_low[0]
                ):

                    pending_buy[0] = 0.0
                    pending_buy_average[0] = nan
                    pending_buy_low[0] = nan
                    pending_buy_bar[0] = -1.0

            # ================================================
            # VALIDATE / EXPIRE PENDING SELL SETUP
            # ================================================

            if (
                pending_sell[0] == 1.0
                and self.bar_index > pending_sell_bar[0]
            ):

                sell_pending_age = (
                    self.bar_index - pending_sell_bar[0]
                )

                if (
                    sell_pending_age > 10.0
                    or self.close[0] > pending_sell_high[0]
                ):

                    pending_sell[0] = 0.0
                    pending_sell_average[0] = nan
                    pending_sell_high[0] = nan
                    pending_sell_bar[0] = -1.0

            # ================================================
            # CHECK BUY PULLBACK ENTRY
            # ================================================

            buy_breakout_pullback_ready = False
            buy_breakout_entry_price = nan

            bullish_pullback_confirmation = (
                self.close[0] > self.open[0]
                and (
                    bullish_rejection
                    or bullish_engulfing
                    or bullish_hammer
                    or bullish_close_momentum
                )
            )

            if (
                pending_buy[0] == 1.0
                and self.bar_index > pending_buy_bar[0]
                and bullish_pullback_confirmation
            ):

                buy_average_touched = (
                    self.low[0] <= pending_buy_average[0]
                    and self.close[0] > pending_buy_average[0]
                )

                buy_bottom_touched = (
                    self.low[0] <= pending_buy_low[0]
                    and self.close[0] > pending_buy_low[0]
                )

                if buy_average_touched:

                    buy_breakout_pullback_ready = True
                    buy_breakout_entry_price = pending_buy_average[0]

                elif buy_bottom_touched:

                    buy_breakout_pullback_ready = True
                    buy_breakout_entry_price = pending_buy_low[0]

            # ================================================
            # CHECK SELL PULLBACK ENTRY
            # ================================================

            sell_breakout_pullback_ready = False
            sell_breakout_entry_price = nan

            bearish_pullback_confirmation = (
                self.close[0] < self.open[0]
                and (
                    bearish_rejection
                    or bearish_engulfing
                    or bearish_shooting_star
                    or bearish_close_momentum
                )
            )

            if (
                pending_sell[0] == 1.0
                and self.bar_index > pending_sell_bar[0]
                and bearish_pullback_confirmation
            ):

                sell_average_touched = (
                    self.high[0] >= pending_sell_average[0]
                    and self.close[0] < pending_sell_average[0]
                )

                sell_top_touched = (
                    self.high[0] >= pending_sell_high[0]
                    and self.close[0] < pending_sell_high[0]
                )

                if sell_average_touched:

                    sell_breakout_pullback_ready = True
                    sell_breakout_entry_price = pending_sell_average[0]

                elif sell_top_touched:

                    sell_breakout_pullback_ready = True
                    sell_breakout_entry_price = pending_sell_high[0]

            # ================================================
            # DYNAMIC DAILY RISK BUDGET
            # ================================================

            if reduced_risk_mode[0] == 1.0:
                total_risk_percent = reduced_risk_percent
            else:
                total_risk_percent = normal_risk_percent

            risk_budget_cash = (
                self.account_capital * total_risk_percent / 100.0
            )

            # Independent original-midpoint setup counter.
            # Resolve every outstanding setup independently before arming this bar's setup.
            # SL/TP wins over midpoint if both are touched on the same candle.
            if self.is_closed_bar:
                if count_1_side[0] != 0.0 and self.bar_index > count_1_bar[0]:
                    count_1_entry_touched = (
                        self.low[0] <= count_1_entry[0]
                        if count_1_side[0] == 1.0 else
                        self.high[0] >= count_1_entry[0]
                    )
                    count_1_sl_touched = (
                        self.low[0] <= count_1_sl[0]
                        if count_1_side[0] == 1.0 else
                        self.high[0] >= count_1_sl[0]
                    )
                    count_1_tp_touched = (
                        self.high[0] >= count_1_tp[0]
                        if count_1_side[0] == 1.0 else
                        self.low[0] <= count_1_tp[0]
                    )
                    if count_1_sl_touched or count_1_tp_touched:
                        if count_1_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_1_side[0] = 0.0
                        count_1_entry[0] = nan
                        count_1_sl[0] = nan
                        count_1_tp[0] = nan
                        count_1_day[0] = nan
                        count_1_bar[0] = -1.0
                    elif count_1_entry_touched:
                        if count_1_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_1_side[0] = 0.0
                        count_1_entry[0] = nan
                        count_1_sl[0] = nan
                        count_1_tp[0] = nan
                        count_1_day[0] = nan
                        count_1_bar[0] = -1.0

                if count_2_side[0] != 0.0 and self.bar_index > count_2_bar[0]:
                    count_2_entry_touched = (
                        self.low[0] <= count_2_entry[0]
                        if count_2_side[0] == 1.0 else
                        self.high[0] >= count_2_entry[0]
                    )
                    count_2_sl_touched = (
                        self.low[0] <= count_2_sl[0]
                        if count_2_side[0] == 1.0 else
                        self.high[0] >= count_2_sl[0]
                    )
                    count_2_tp_touched = (
                        self.high[0] >= count_2_tp[0]
                        if count_2_side[0] == 1.0 else
                        self.low[0] <= count_2_tp[0]
                    )
                    if count_2_sl_touched or count_2_tp_touched:
                        if count_2_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_2_side[0] = 0.0
                        count_2_entry[0] = nan
                        count_2_sl[0] = nan
                        count_2_tp[0] = nan
                        count_2_day[0] = nan
                        count_2_bar[0] = -1.0
                    elif count_2_entry_touched:
                        if count_2_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_2_side[0] = 0.0
                        count_2_entry[0] = nan
                        count_2_sl[0] = nan
                        count_2_tp[0] = nan
                        count_2_day[0] = nan
                        count_2_bar[0] = -1.0

                if count_3_side[0] != 0.0 and self.bar_index > count_3_bar[0]:
                    count_3_entry_touched = (
                        self.low[0] <= count_3_entry[0]
                        if count_3_side[0] == 1.0 else
                        self.high[0] >= count_3_entry[0]
                    )
                    count_3_sl_touched = (
                        self.low[0] <= count_3_sl[0]
                        if count_3_side[0] == 1.0 else
                        self.high[0] >= count_3_sl[0]
                    )
                    count_3_tp_touched = (
                        self.high[0] >= count_3_tp[0]
                        if count_3_side[0] == 1.0 else
                        self.low[0] <= count_3_tp[0]
                    )
                    if count_3_sl_touched or count_3_tp_touched:
                        if count_3_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_3_side[0] = 0.0
                        count_3_entry[0] = nan
                        count_3_sl[0] = nan
                        count_3_tp[0] = nan
                        count_3_day[0] = nan
                        count_3_bar[0] = -1.0
                    elif count_3_entry_touched:
                        if count_3_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_3_side[0] = 0.0
                        count_3_entry[0] = nan
                        count_3_sl[0] = nan
                        count_3_tp[0] = nan
                        count_3_day[0] = nan
                        count_3_bar[0] = -1.0

                if count_4_side[0] != 0.0 and self.bar_index > count_4_bar[0]:
                    count_4_entry_touched = (
                        self.low[0] <= count_4_entry[0]
                        if count_4_side[0] == 1.0 else
                        self.high[0] >= count_4_entry[0]
                    )
                    count_4_sl_touched = (
                        self.low[0] <= count_4_sl[0]
                        if count_4_side[0] == 1.0 else
                        self.high[0] >= count_4_sl[0]
                    )
                    count_4_tp_touched = (
                        self.high[0] >= count_4_tp[0]
                        if count_4_side[0] == 1.0 else
                        self.low[0] <= count_4_tp[0]
                    )
                    if count_4_sl_touched or count_4_tp_touched:
                        if count_4_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_4_side[0] = 0.0
                        count_4_entry[0] = nan
                        count_4_sl[0] = nan
                        count_4_tp[0] = nan
                        count_4_day[0] = nan
                        count_4_bar[0] = -1.0
                    elif count_4_entry_touched:
                        if count_4_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_4_side[0] = 0.0
                        count_4_entry[0] = nan
                        count_4_sl[0] = nan
                        count_4_tp[0] = nan
                        count_4_day[0] = nan
                        count_4_bar[0] = -1.0

                if count_5_side[0] != 0.0 and self.bar_index > count_5_bar[0]:
                    count_5_entry_touched = (
                        self.low[0] <= count_5_entry[0]
                        if count_5_side[0] == 1.0 else
                        self.high[0] >= count_5_entry[0]
                    )
                    count_5_sl_touched = (
                        self.low[0] <= count_5_sl[0]
                        if count_5_side[0] == 1.0 else
                        self.high[0] >= count_5_sl[0]
                    )
                    count_5_tp_touched = (
                        self.high[0] >= count_5_tp[0]
                        if count_5_side[0] == 1.0 else
                        self.low[0] <= count_5_tp[0]
                    )
                    if count_5_sl_touched or count_5_tp_touched:
                        if count_5_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_5_side[0] = 0.0
                        count_5_entry[0] = nan
                        count_5_sl[0] = nan
                        count_5_tp[0] = nan
                        count_5_day[0] = nan
                        count_5_bar[0] = -1.0
                    elif count_5_entry_touched:
                        if count_5_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_5_side[0] = 0.0
                        count_5_entry[0] = nan
                        count_5_sl[0] = nan
                        count_5_tp[0] = nan
                        count_5_day[0] = nan
                        count_5_bar[0] = -1.0

                if count_6_side[0] != 0.0 and self.bar_index > count_6_bar[0]:
                    count_6_entry_touched = (
                        self.low[0] <= count_6_entry[0]
                        if count_6_side[0] == 1.0 else
                        self.high[0] >= count_6_entry[0]
                    )
                    count_6_sl_touched = (
                        self.low[0] <= count_6_sl[0]
                        if count_6_side[0] == 1.0 else
                        self.high[0] >= count_6_sl[0]
                    )
                    count_6_tp_touched = (
                        self.high[0] >= count_6_tp[0]
                        if count_6_side[0] == 1.0 else
                        self.low[0] <= count_6_tp[0]
                    )
                    if count_6_sl_touched or count_6_tp_touched:
                        if count_6_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_6_side[0] = 0.0
                        count_6_entry[0] = nan
                        count_6_sl[0] = nan
                        count_6_tp[0] = nan
                        count_6_day[0] = nan
                        count_6_bar[0] = -1.0
                    elif count_6_entry_touched:
                        if count_6_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_6_side[0] = 0.0
                        count_6_entry[0] = nan
                        count_6_sl[0] = nan
                        count_6_tp[0] = nan
                        count_6_day[0] = nan
                        count_6_bar[0] = -1.0

                if count_7_side[0] != 0.0 and self.bar_index > count_7_bar[0]:
                    count_7_entry_touched = (
                        self.low[0] <= count_7_entry[0]
                        if count_7_side[0] == 1.0 else
                        self.high[0] >= count_7_entry[0]
                    )
                    count_7_sl_touched = (
                        self.low[0] <= count_7_sl[0]
                        if count_7_side[0] == 1.0 else
                        self.high[0] >= count_7_sl[0]
                    )
                    count_7_tp_touched = (
                        self.high[0] >= count_7_tp[0]
                        if count_7_side[0] == 1.0 else
                        self.low[0] <= count_7_tp[0]
                    )
                    if count_7_sl_touched or count_7_tp_touched:
                        if count_7_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_7_side[0] = 0.0
                        count_7_entry[0] = nan
                        count_7_sl[0] = nan
                        count_7_tp[0] = nan
                        count_7_day[0] = nan
                        count_7_bar[0] = -1.0
                    elif count_7_entry_touched:
                        if count_7_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_7_side[0] = 0.0
                        count_7_entry[0] = nan
                        count_7_sl[0] = nan
                        count_7_tp[0] = nan
                        count_7_day[0] = nan
                        count_7_bar[0] = -1.0

                if count_8_side[0] != 0.0 and self.bar_index > count_8_bar[0]:
                    count_8_entry_touched = (
                        self.low[0] <= count_8_entry[0]
                        if count_8_side[0] == 1.0 else
                        self.high[0] >= count_8_entry[0]
                    )
                    count_8_sl_touched = (
                        self.low[0] <= count_8_sl[0]
                        if count_8_side[0] == 1.0 else
                        self.high[0] >= count_8_sl[0]
                    )
                    count_8_tp_touched = (
                        self.high[0] >= count_8_tp[0]
                        if count_8_side[0] == 1.0 else
                        self.low[0] <= count_8_tp[0]
                    )
                    if count_8_sl_touched or count_8_tp_touched:
                        if count_8_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_8_side[0] = 0.0
                        count_8_entry[0] = nan
                        count_8_sl[0] = nan
                        count_8_tp[0] = nan
                        count_8_day[0] = nan
                        count_8_bar[0] = -1.0
                    elif count_8_entry_touched:
                        if count_8_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_8_side[0] = 0.0
                        count_8_entry[0] = nan
                        count_8_sl[0] = nan
                        count_8_tp[0] = nan
                        count_8_day[0] = nan
                        count_8_bar[0] = -1.0

                if count_9_side[0] != 0.0 and self.bar_index > count_9_bar[0]:
                    count_9_entry_touched = (
                        self.low[0] <= count_9_entry[0]
                        if count_9_side[0] == 1.0 else
                        self.high[0] >= count_9_entry[0]
                    )
                    count_9_sl_touched = (
                        self.low[0] <= count_9_sl[0]
                        if count_9_side[0] == 1.0 else
                        self.high[0] >= count_9_sl[0]
                    )
                    count_9_tp_touched = (
                        self.high[0] >= count_9_tp[0]
                        if count_9_side[0] == 1.0 else
                        self.low[0] <= count_9_tp[0]
                    )
                    if count_9_sl_touched or count_9_tp_touched:
                        if count_9_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_9_side[0] = 0.0
                        count_9_entry[0] = nan
                        count_9_sl[0] = nan
                        count_9_tp[0] = nan
                        count_9_day[0] = nan
                        count_9_bar[0] = -1.0
                    elif count_9_entry_touched:
                        if count_9_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_9_side[0] = 0.0
                        count_9_entry[0] = nan
                        count_9_sl[0] = nan
                        count_9_tp[0] = nan
                        count_9_day[0] = nan
                        count_9_bar[0] = -1.0

                if count_10_side[0] != 0.0 and self.bar_index > count_10_bar[0]:
                    count_10_entry_touched = (
                        self.low[0] <= count_10_entry[0]
                        if count_10_side[0] == 1.0 else
                        self.high[0] >= count_10_entry[0]
                    )
                    count_10_sl_touched = (
                        self.low[0] <= count_10_sl[0]
                        if count_10_side[0] == 1.0 else
                        self.high[0] >= count_10_sl[0]
                    )
                    count_10_tp_touched = (
                        self.high[0] >= count_10_tp[0]
                        if count_10_side[0] == 1.0 else
                        self.low[0] <= count_10_tp[0]
                    )
                    if count_10_sl_touched or count_10_tp_touched:
                        if count_10_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_10_side[0] = 0.0
                        count_10_entry[0] = nan
                        count_10_sl[0] = nan
                        count_10_tp[0] = nan
                        count_10_day[0] = nan
                        count_10_bar[0] = -1.0
                    elif count_10_entry_touched:
                        if count_10_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_10_side[0] = 0.0
                        count_10_entry[0] = nan
                        count_10_sl[0] = nan
                        count_10_tp[0] = nan
                        count_10_day[0] = nan
                        count_10_bar[0] = -1.0

                if count_11_side[0] != 0.0 and self.bar_index > count_11_bar[0]:
                    count_11_entry_touched = (
                        self.low[0] <= count_11_entry[0]
                        if count_11_side[0] == 1.0 else
                        self.high[0] >= count_11_entry[0]
                    )
                    count_11_sl_touched = (
                        self.low[0] <= count_11_sl[0]
                        if count_11_side[0] == 1.0 else
                        self.high[0] >= count_11_sl[0]
                    )
                    count_11_tp_touched = (
                        self.high[0] >= count_11_tp[0]
                        if count_11_side[0] == 1.0 else
                        self.low[0] <= count_11_tp[0]
                    )
                    if count_11_sl_touched or count_11_tp_touched:
                        if count_11_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_11_side[0] = 0.0
                        count_11_entry[0] = nan
                        count_11_sl[0] = nan
                        count_11_tp[0] = nan
                        count_11_day[0] = nan
                        count_11_bar[0] = -1.0
                    elif count_11_entry_touched:
                        if count_11_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_11_side[0] = 0.0
                        count_11_entry[0] = nan
                        count_11_sl[0] = nan
                        count_11_tp[0] = nan
                        count_11_day[0] = nan
                        count_11_bar[0] = -1.0

                if count_12_side[0] != 0.0 and self.bar_index > count_12_bar[0]:
                    count_12_entry_touched = (
                        self.low[0] <= count_12_entry[0]
                        if count_12_side[0] == 1.0 else
                        self.high[0] >= count_12_entry[0]
                    )
                    count_12_sl_touched = (
                        self.low[0] <= count_12_sl[0]
                        if count_12_side[0] == 1.0 else
                        self.high[0] >= count_12_sl[0]
                    )
                    count_12_tp_touched = (
                        self.high[0] >= count_12_tp[0]
                        if count_12_side[0] == 1.0 else
                        self.low[0] <= count_12_tp[0]
                    )
                    if count_12_sl_touched or count_12_tp_touched:
                        if count_12_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_12_side[0] = 0.0
                        count_12_entry[0] = nan
                        count_12_sl[0] = nan
                        count_12_tp[0] = nan
                        count_12_day[0] = nan
                        count_12_bar[0] = -1.0
                    elif count_12_entry_touched:
                        if count_12_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_12_side[0] = 0.0
                        count_12_entry[0] = nan
                        count_12_sl[0] = nan
                        count_12_tp[0] = nan
                        count_12_day[0] = nan
                        count_12_bar[0] = -1.0

                if count_13_side[0] != 0.0 and self.bar_index > count_13_bar[0]:
                    count_13_entry_touched = (
                        self.low[0] <= count_13_entry[0]
                        if count_13_side[0] == 1.0 else
                        self.high[0] >= count_13_entry[0]
                    )
                    count_13_sl_touched = (
                        self.low[0] <= count_13_sl[0]
                        if count_13_side[0] == 1.0 else
                        self.high[0] >= count_13_sl[0]
                    )
                    count_13_tp_touched = (
                        self.high[0] >= count_13_tp[0]
                        if count_13_side[0] == 1.0 else
                        self.low[0] <= count_13_tp[0]
                    )
                    if count_13_sl_touched or count_13_tp_touched:
                        if count_13_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_13_side[0] = 0.0
                        count_13_entry[0] = nan
                        count_13_sl[0] = nan
                        count_13_tp[0] = nan
                        count_13_day[0] = nan
                        count_13_bar[0] = -1.0
                    elif count_13_entry_touched:
                        if count_13_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_13_side[0] = 0.0
                        count_13_entry[0] = nan
                        count_13_sl[0] = nan
                        count_13_tp[0] = nan
                        count_13_day[0] = nan
                        count_13_bar[0] = -1.0

                if count_14_side[0] != 0.0 and self.bar_index > count_14_bar[0]:
                    count_14_entry_touched = (
                        self.low[0] <= count_14_entry[0]
                        if count_14_side[0] == 1.0 else
                        self.high[0] >= count_14_entry[0]
                    )
                    count_14_sl_touched = (
                        self.low[0] <= count_14_sl[0]
                        if count_14_side[0] == 1.0 else
                        self.high[0] >= count_14_sl[0]
                    )
                    count_14_tp_touched = (
                        self.high[0] >= count_14_tp[0]
                        if count_14_side[0] == 1.0 else
                        self.low[0] <= count_14_tp[0]
                    )
                    if count_14_sl_touched or count_14_tp_touched:
                        if count_14_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_14_side[0] = 0.0
                        count_14_entry[0] = nan
                        count_14_sl[0] = nan
                        count_14_tp[0] = nan
                        count_14_day[0] = nan
                        count_14_bar[0] = -1.0
                    elif count_14_entry_touched:
                        if count_14_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_14_side[0] = 0.0
                        count_14_entry[0] = nan
                        count_14_sl[0] = nan
                        count_14_tp[0] = nan
                        count_14_day[0] = nan
                        count_14_bar[0] = -1.0

                if count_15_side[0] != 0.0 and self.bar_index > count_15_bar[0]:
                    count_15_entry_touched = (
                        self.low[0] <= count_15_entry[0]
                        if count_15_side[0] == 1.0 else
                        self.high[0] >= count_15_entry[0]
                    )
                    count_15_sl_touched = (
                        self.low[0] <= count_15_sl[0]
                        if count_15_side[0] == 1.0 else
                        self.high[0] >= count_15_sl[0]
                    )
                    count_15_tp_touched = (
                        self.high[0] >= count_15_tp[0]
                        if count_15_side[0] == 1.0 else
                        self.low[0] <= count_15_tp[0]
                    )
                    if count_15_sl_touched or count_15_tp_touched:
                        if count_15_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_15_side[0] = 0.0
                        count_15_entry[0] = nan
                        count_15_sl[0] = nan
                        count_15_tp[0] = nan
                        count_15_day[0] = nan
                        count_15_bar[0] = -1.0
                    elif count_15_entry_touched:
                        if count_15_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_15_side[0] = 0.0
                        count_15_entry[0] = nan
                        count_15_sl[0] = nan
                        count_15_tp[0] = nan
                        count_15_day[0] = nan
                        count_15_bar[0] = -1.0

                if count_16_side[0] != 0.0 and self.bar_index > count_16_bar[0]:
                    count_16_entry_touched = (
                        self.low[0] <= count_16_entry[0]
                        if count_16_side[0] == 1.0 else
                        self.high[0] >= count_16_entry[0]
                    )
                    count_16_sl_touched = (
                        self.low[0] <= count_16_sl[0]
                        if count_16_side[0] == 1.0 else
                        self.high[0] >= count_16_sl[0]
                    )
                    count_16_tp_touched = (
                        self.high[0] >= count_16_tp[0]
                        if count_16_side[0] == 1.0 else
                        self.low[0] <= count_16_tp[0]
                    )
                    if count_16_sl_touched or count_16_tp_touched:
                        if count_16_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_16_side[0] = 0.0
                        count_16_entry[0] = nan
                        count_16_sl[0] = nan
                        count_16_tp[0] = nan
                        count_16_day[0] = nan
                        count_16_bar[0] = -1.0
                    elif count_16_entry_touched:
                        if count_16_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_16_side[0] = 0.0
                        count_16_entry[0] = nan
                        count_16_sl[0] = nan
                        count_16_tp[0] = nan
                        count_16_day[0] = nan
                        count_16_bar[0] = -1.0

                if count_17_side[0] != 0.0 and self.bar_index > count_17_bar[0]:
                    count_17_entry_touched = (
                        self.low[0] <= count_17_entry[0]
                        if count_17_side[0] == 1.0 else
                        self.high[0] >= count_17_entry[0]
                    )
                    count_17_sl_touched = (
                        self.low[0] <= count_17_sl[0]
                        if count_17_side[0] == 1.0 else
                        self.high[0] >= count_17_sl[0]
                    )
                    count_17_tp_touched = (
                        self.high[0] >= count_17_tp[0]
                        if count_17_side[0] == 1.0 else
                        self.low[0] <= count_17_tp[0]
                    )
                    if count_17_sl_touched or count_17_tp_touched:
                        if count_17_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_17_side[0] = 0.0
                        count_17_entry[0] = nan
                        count_17_sl[0] = nan
                        count_17_tp[0] = nan
                        count_17_day[0] = nan
                        count_17_bar[0] = -1.0
                    elif count_17_entry_touched:
                        if count_17_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_17_side[0] = 0.0
                        count_17_entry[0] = nan
                        count_17_sl[0] = nan
                        count_17_tp[0] = nan
                        count_17_day[0] = nan
                        count_17_bar[0] = -1.0

                if count_18_side[0] != 0.0 and self.bar_index > count_18_bar[0]:
                    count_18_entry_touched = (
                        self.low[0] <= count_18_entry[0]
                        if count_18_side[0] == 1.0 else
                        self.high[0] >= count_18_entry[0]
                    )
                    count_18_sl_touched = (
                        self.low[0] <= count_18_sl[0]
                        if count_18_side[0] == 1.0 else
                        self.high[0] >= count_18_sl[0]
                    )
                    count_18_tp_touched = (
                        self.high[0] >= count_18_tp[0]
                        if count_18_side[0] == 1.0 else
                        self.low[0] <= count_18_tp[0]
                    )
                    if count_18_sl_touched or count_18_tp_touched:
                        if count_18_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_18_side[0] = 0.0
                        count_18_entry[0] = nan
                        count_18_sl[0] = nan
                        count_18_tp[0] = nan
                        count_18_day[0] = nan
                        count_18_bar[0] = -1.0
                    elif count_18_entry_touched:
                        if count_18_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_18_side[0] = 0.0
                        count_18_entry[0] = nan
                        count_18_sl[0] = nan
                        count_18_tp[0] = nan
                        count_18_day[0] = nan
                        count_18_bar[0] = -1.0

                if count_19_side[0] != 0.0 and self.bar_index > count_19_bar[0]:
                    count_19_entry_touched = (
                        self.low[0] <= count_19_entry[0]
                        if count_19_side[0] == 1.0 else
                        self.high[0] >= count_19_entry[0]
                    )
                    count_19_sl_touched = (
                        self.low[0] <= count_19_sl[0]
                        if count_19_side[0] == 1.0 else
                        self.high[0] >= count_19_sl[0]
                    )
                    count_19_tp_touched = (
                        self.high[0] >= count_19_tp[0]
                        if count_19_side[0] == 1.0 else
                        self.low[0] <= count_19_tp[0]
                    )
                    if count_19_sl_touched or count_19_tp_touched:
                        if count_19_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_19_side[0] = 0.0
                        count_19_entry[0] = nan
                        count_19_sl[0] = nan
                        count_19_tp[0] = nan
                        count_19_day[0] = nan
                        count_19_bar[0] = -1.0
                    elif count_19_entry_touched:
                        if count_19_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_19_side[0] = 0.0
                        count_19_entry[0] = nan
                        count_19_sl[0] = nan
                        count_19_tp[0] = nan
                        count_19_day[0] = nan
                        count_19_bar[0] = -1.0

                if count_20_side[0] != 0.0 and self.bar_index > count_20_bar[0]:
                    count_20_entry_touched = (
                        self.low[0] <= count_20_entry[0]
                        if count_20_side[0] == 1.0 else
                        self.high[0] >= count_20_entry[0]
                    )
                    count_20_sl_touched = (
                        self.low[0] <= count_20_sl[0]
                        if count_20_side[0] == 1.0 else
                        self.high[0] >= count_20_sl[0]
                    )
                    count_20_tp_touched = (
                        self.high[0] >= count_20_tp[0]
                        if count_20_side[0] == 1.0 else
                        self.low[0] <= count_20_tp[0]
                    )
                    if count_20_sl_touched or count_20_tp_touched:
                        if count_20_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_20_side[0] = 0.0
                        count_20_entry[0] = nan
                        count_20_sl[0] = nan
                        count_20_tp[0] = nan
                        count_20_day[0] = nan
                        count_20_bar[0] = -1.0
                    elif count_20_entry_touched:
                        if count_20_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_20_side[0] = 0.0
                        count_20_entry[0] = nan
                        count_20_sl[0] = nan
                        count_20_tp[0] = nan
                        count_20_day[0] = nan
                        count_20_bar[0] = -1.0

                if not rr_setting_changed:
                    count_sell_ready = sell_condition or sell_breakout_pullback_ready
                    count_buy_ready = buy_condition or buy_breakout_pullback_ready

                    if count_sell_ready and not count_buy_ready:
                        count_new_entry = candidate_entry_price
                        count_recent_high = max([
                            self.high[0], self.high[1], self.high[2], self.high[3],
                            self.high[4], self.high[5], self.high[6], self.high[7]
                        ])
                        count_stop_buffer = max(candle_range * 0.25, abs(count_new_entry) * 0.00005)
                        count_new_stop = max(count_recent_high, count_new_entry + count_stop_buffer)
                        count_new_risk = count_new_stop - count_new_entry
                        count_new_distance = abs(count_new_entry - count_new_stop)
                        count_new_side = -1.0
                    elif count_buy_ready:
                        count_new_entry = candidate_entry_price
                        count_recent_low = min([
                            self.low[0], self.low[1], self.low[2], self.low[3],
                            self.low[4], self.low[5], self.low[6], self.low[7]
                        ])
                        count_stop_buffer = max(candle_range * 0.25, abs(count_new_entry) * 0.00005)
                        count_new_stop = min(count_recent_low, count_new_entry - count_stop_buffer)
                        count_new_risk = count_new_entry - count_new_stop
                        count_new_distance = abs(count_new_entry - count_new_stop)
                        count_new_side = 1.0
                    else:
                        count_new_risk = 0.0
                        count_new_distance = 0.0

                    count_new_risk_per_lot = count_new_distance * self.contract_size
                    count_new_lot = 0.0
                    if count_new_risk_per_lot > 0.0 and risk_budget_cash > 0.0:
                        count_new_lot = int((risk_budget_cash / count_new_risk_per_lot) * 100.0) / 100.0

                    if (
                        count_new_side != 0.0
                        and count_new_risk > 0.0
                        and count_new_distance <= maximum_allowed_sl_distance
                        and count_new_lot >= 0.01
                    ):
                        if count_1_side[0] == 0.0:
                            count_1_side[0] = count_new_side
                            count_1_entry[0] = count_new_entry
                            count_1_sl[0] = count_new_stop
                            count_1_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_1_day[0] = current_ist_day_key
                            count_1_bar[0] = float(self.bar_index)
                        elif count_2_side[0] == 0.0:
                            count_2_side[0] = count_new_side
                            count_2_entry[0] = count_new_entry
                            count_2_sl[0] = count_new_stop
                            count_2_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_2_day[0] = current_ist_day_key
                            count_2_bar[0] = float(self.bar_index)
                        elif count_3_side[0] == 0.0:
                            count_3_side[0] = count_new_side
                            count_3_entry[0] = count_new_entry
                            count_3_sl[0] = count_new_stop
                            count_3_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_3_day[0] = current_ist_day_key
                            count_3_bar[0] = float(self.bar_index)
                        elif count_4_side[0] == 0.0:
                            count_4_side[0] = count_new_side
                            count_4_entry[0] = count_new_entry
                            count_4_sl[0] = count_new_stop
                            count_4_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_4_day[0] = current_ist_day_key
                            count_4_bar[0] = float(self.bar_index)
                        elif count_5_side[0] == 0.0:
                            count_5_side[0] = count_new_side
                            count_5_entry[0] = count_new_entry
                            count_5_sl[0] = count_new_stop
                            count_5_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_5_day[0] = current_ist_day_key
                            count_5_bar[0] = float(self.bar_index)
                        elif count_6_side[0] == 0.0:
                            count_6_side[0] = count_new_side
                            count_6_entry[0] = count_new_entry
                            count_6_sl[0] = count_new_stop
                            count_6_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_6_day[0] = current_ist_day_key
                            count_6_bar[0] = float(self.bar_index)
                        elif count_7_side[0] == 0.0:
                            count_7_side[0] = count_new_side
                            count_7_entry[0] = count_new_entry
                            count_7_sl[0] = count_new_stop
                            count_7_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_7_day[0] = current_ist_day_key
                            count_7_bar[0] = float(self.bar_index)
                        elif count_8_side[0] == 0.0:
                            count_8_side[0] = count_new_side
                            count_8_entry[0] = count_new_entry
                            count_8_sl[0] = count_new_stop
                            count_8_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_8_day[0] = current_ist_day_key
                            count_8_bar[0] = float(self.bar_index)
                        elif count_9_side[0] == 0.0:
                            count_9_side[0] = count_new_side
                            count_9_entry[0] = count_new_entry
                            count_9_sl[0] = count_new_stop
                            count_9_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_9_day[0] = current_ist_day_key
                            count_9_bar[0] = float(self.bar_index)
                        elif count_10_side[0] == 0.0:
                            count_10_side[0] = count_new_side
                            count_10_entry[0] = count_new_entry
                            count_10_sl[0] = count_new_stop
                            count_10_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_10_day[0] = current_ist_day_key
                            count_10_bar[0] = float(self.bar_index)
                        elif count_11_side[0] == 0.0:
                            count_11_side[0] = count_new_side
                            count_11_entry[0] = count_new_entry
                            count_11_sl[0] = count_new_stop
                            count_11_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_11_day[0] = current_ist_day_key
                            count_11_bar[0] = float(self.bar_index)
                        elif count_12_side[0] == 0.0:
                            count_12_side[0] = count_new_side
                            count_12_entry[0] = count_new_entry
                            count_12_sl[0] = count_new_stop
                            count_12_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_12_day[0] = current_ist_day_key
                            count_12_bar[0] = float(self.bar_index)
                        elif count_13_side[0] == 0.0:
                            count_13_side[0] = count_new_side
                            count_13_entry[0] = count_new_entry
                            count_13_sl[0] = count_new_stop
                            count_13_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_13_day[0] = current_ist_day_key
                            count_13_bar[0] = float(self.bar_index)
                        elif count_14_side[0] == 0.0:
                            count_14_side[0] = count_new_side
                            count_14_entry[0] = count_new_entry
                            count_14_sl[0] = count_new_stop
                            count_14_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_14_day[0] = current_ist_day_key
                            count_14_bar[0] = float(self.bar_index)
                        elif count_15_side[0] == 0.0:
                            count_15_side[0] = count_new_side
                            count_15_entry[0] = count_new_entry
                            count_15_sl[0] = count_new_stop
                            count_15_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_15_day[0] = current_ist_day_key
                            count_15_bar[0] = float(self.bar_index)
                        elif count_16_side[0] == 0.0:
                            count_16_side[0] = count_new_side
                            count_16_entry[0] = count_new_entry
                            count_16_sl[0] = count_new_stop
                            count_16_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_16_day[0] = current_ist_day_key
                            count_16_bar[0] = float(self.bar_index)
                        elif count_17_side[0] == 0.0:
                            count_17_side[0] = count_new_side
                            count_17_entry[0] = count_new_entry
                            count_17_sl[0] = count_new_stop
                            count_17_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_17_day[0] = current_ist_day_key
                            count_17_bar[0] = float(self.bar_index)
                        elif count_18_side[0] == 0.0:
                            count_18_side[0] = count_new_side
                            count_18_entry[0] = count_new_entry
                            count_18_sl[0] = count_new_stop
                            count_18_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_18_day[0] = current_ist_day_key
                            count_18_bar[0] = float(self.bar_index)
                        elif count_19_side[0] == 0.0:
                            count_19_side[0] = count_new_side
                            count_19_entry[0] = count_new_entry
                            count_19_sl[0] = count_new_stop
                            count_19_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_19_day[0] = current_ist_day_key
                            count_19_bar[0] = float(self.bar_index)
                        elif count_20_side[0] == 0.0:
                            count_20_side[0] = count_new_side
                            count_20_entry[0] = count_new_entry
                            count_20_sl[0] = count_new_stop
                            count_20_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_20_day[0] = current_ist_day_key
                            count_20_bar[0] = float(self.bar_index)
                        # If all 20 slots are occupied, do not overwrite an unresolved setup.
            # ================================================
            # NEW PRIMARY ENTRY
            # ================================================

            # Never commit an entry, set active trade state, or expose an
            # absolute entry marker while this candle is still forming.
            # Setup conditions may develop intrabar, but the final entry/SL/TP
            # calculation is committed only on the candle-close callback.
            if (
                self.is_closed_bar and side[0] == 0.0
                and pending_trade_side[0] == 0.0 and not trade_exited
            ):

                # Preserve the original signal conditions without a deviation
                # filter. Entry 1 uses the confirmation candle midpoint.
                sell_entry_ready = sell_condition or sell_breakout_pullback_ready
                buy_entry_ready = buy_condition or buy_breakout_pullback_ready

                if sell_entry_ready and not buy_entry_ready:

                    recent_high = max([
                        self.high[0], self.high[1],
                        self.high[2], self.high[3],
                        self.high[4], self.high[5],
                        self.high[6], self.high[7]
                    ])

                    # Preserve the original midpoint setup and sizing exactly.
                    # The midpoint determines the original SL, TP and total lot.
                    entry_price = candidate_entry_price

                    if sell_breakout_pullback_ready:
                        sell_reason = 'BREAKOUT + VOLUME PULLBACK'

                    stop_price = recent_high
                    entry_stop_buffer = max(
                        candle_range * 0.25,
                        abs(entry_price) * 0.00005
                    )
                    stop_price = max(
                        stop_price,
                        entry_price + entry_stop_buffer
                    )

                    risk = stop_price - entry_price
                    sl_distance = abs(entry_price - stop_price)
                    risk_per_one_lot = sl_distance * self.contract_size
                    calculated_lot = 0.0
                    calculated_risk_cash = nan

                    if risk_per_one_lot > 0.0 and risk_budget_cash > 0.0:
                        raw_lot = risk_budget_cash / risk_per_one_lot
                        calculated_lot = int(raw_lot * 100.0) / 100.0
                        calculated_risk_cash = (
                            calculated_lot * risk_per_one_lot
                        )

                    # Allocate half of the dollar risk budget to the midpoint leg.
                    # The remaining budget is reserved for the immediate leg after midpoint fill.
                    midpoint_risk_per_lot = sl_distance * self.contract_size
                    mid_lot = 0.0
                    if midpoint_risk_per_lot > 0.0 and risk_budget_cash > 0.0:
                        midpoint_half_budget = risk_budget_cash * 0.50
                        mid_lot = int((midpoint_half_budget / midpoint_risk_per_lot) * 100.0) / 100.0

                    mid_risk_cash_value = mid_lot * midpoint_risk_per_lot

                    if (
                        risk > 0.0
                        and sl_distance <= maximum_allowed_sl_distance
                        and mid_lot >= 0.01
                        and mid_risk_cash_value <= risk_budget_cash
                    ):
                        target_price = entry_price - risk * rr_multiplier

                        # Arm only a pending midpoint order. No active side,
                        # trade P/L, or immediate entry is recorded yet.
                        pending_trade_side[0] = -1.0
                        pending_trade_entry[0] = entry_price
                        pending_mid_entry[0] = entry_price
                        pending_trade_sl[0] = stop_price
                        pending_trade_tp[0] = target_price
                        pending_trade_lot[0] = mid_lot
                        pending_trade_risk_cash[0] = mid_risk_cash_value
                        pending_trade_setup_day[0] = current_ist_day_key
                        pending_trade_setup_bar[0] = float(self.bar_index)

                        entry[0] = nan
                        midpoint_master_entry[0] = entry_price
                        early_leg_entry[0] = entry_price
                        early_leg_lot[0] = 0.0
                        mid_leg_lot[0] = mid_lot
                        mid_leg_active[0] = 0.0
                        early_leg_closed[0] = 0.0
                        early_leg_pnl[0] = 0.0
                        mid_leg_pnl[0] = 0.0
                        setup_risk_budget[0] = risk_budget_cash
                        sl[0] = stop_price
                        tp[0] = target_price
                        side[0] = 0.0
                        trade_lot[0] = nan
                        trade_risk_cash[0] = nan
                        original_risk_distance[0] = sl_distance
                        favorable_extreme[0] = entry_price
                        trail_candidate[0] = nan
                        trail_confirm_count[0] = 0.0
                        trail_stage[0] = 0.0
                        trail_last_update_bar[0] = -1.0
                        early_exit_warned[0] = 0.0
                        entry_count[0] = 0.0
                        last_entry_bar[0] = -1.0
                        last_entry_price[0] = nan
                        entry_label_time[0] = self.time[0]
                        pending_early_entry[0] = nan
                        sell_signal = True

                        pending_buy[0] = 0.0
                        pending_buy_average[0] = nan
                        pending_buy_low[0] = nan
                        pending_buy_bar[0] = -1.0
                        pending_sell[0] = 0.0
                        pending_sell_average[0] = nan
                        pending_sell_high[0] = nan
                        pending_sell_bar[0] = -1.0

                elif buy_entry_ready:

                    recent_low = min([
                        self.low[0], self.low[1],
                        self.low[2], self.low[3],
                        self.low[4], self.low[5],
                        self.low[6], self.low[7]
                    ])

                    # Preserve the original midpoint setup and sizing exactly.
                    # The midpoint determines the original SL, TP and total lot.
                    entry_price = candidate_entry_price

                    if buy_breakout_pullback_ready:
                        buy_reason = 'BREAKOUT + VOLUME PULLBACK'

                    stop_price = recent_low
                    entry_stop_buffer = max(
                        candle_range * 0.25,
                        abs(entry_price) * 0.00005
                    )
                    stop_price = min(
                        stop_price,
                        entry_price - entry_stop_buffer
                    )

                    risk = entry_price - stop_price
                    sl_distance = abs(entry_price - stop_price)
                    risk_per_one_lot = sl_distance * self.contract_size
                    calculated_lot = 0.0
                    calculated_risk_cash = nan

                    if risk_per_one_lot > 0.0 and risk_budget_cash > 0.0:
                        raw_lot = risk_budget_cash / risk_per_one_lot
                        calculated_lot = int(raw_lot * 100.0) / 100.0
                        calculated_risk_cash = (
                            calculated_lot * risk_per_one_lot
                        )

                    # Allocate half of the dollar risk budget to the midpoint leg.
                    # The remaining budget is reserved for the immediate leg after midpoint fill.
                    midpoint_risk_per_lot = sl_distance * self.contract_size
                    mid_lot = 0.0
                    if midpoint_risk_per_lot > 0.0 and risk_budget_cash > 0.0:
                        midpoint_half_budget = risk_budget_cash * 0.50
                        mid_lot = int((midpoint_half_budget / midpoint_risk_per_lot) * 100.0) / 100.0

                    mid_risk_cash_value = mid_lot * midpoint_risk_per_lot

                    if (
                        risk > 0.0
                        and sl_distance <= maximum_allowed_sl_distance
                        and mid_lot >= 0.01
                        and mid_risk_cash_value <= risk_budget_cash
                    ):
                        target_price = entry_price + risk * rr_multiplier

                        # Arm only a pending midpoint order. No active side,
                        # trade P/L, or immediate entry is recorded yet.
                        pending_trade_side[0] = 1.0
                        pending_trade_entry[0] = entry_price
                        pending_mid_entry[0] = entry_price
                        pending_trade_sl[0] = stop_price
                        pending_trade_tp[0] = target_price
                        pending_trade_lot[0] = mid_lot
                        pending_trade_risk_cash[0] = mid_risk_cash_value
                        pending_trade_setup_day[0] = current_ist_day_key
                        pending_trade_setup_bar[0] = float(self.bar_index)

                        entry[0] = nan
                        midpoint_master_entry[0] = entry_price
                        early_leg_entry[0] = entry_price
                        early_leg_lot[0] = 0.0
                        mid_leg_lot[0] = mid_lot
                        mid_leg_active[0] = 0.0
                        early_leg_closed[0] = 0.0
                        early_leg_pnl[0] = 0.0
                        mid_leg_pnl[0] = 0.0
                        setup_risk_budget[0] = risk_budget_cash
                        sl[0] = stop_price
                        tp[0] = target_price
                        side[0] = 0.0
                        trade_lot[0] = nan
                        trade_risk_cash[0] = nan
                        original_risk_distance[0] = sl_distance
                        favorable_extreme[0] = entry_price
                        trail_candidate[0] = nan
                        trail_confirm_count[0] = 0.0
                        trail_stage[0] = 0.0
                        trail_last_update_bar[0] = -1.0
                        early_exit_warned[0] = 0.0
                        entry_count[0] = 0.0
                        last_entry_bar[0] = -1.0
                        last_entry_price[0] = nan
                        entry_label_time[0] = self.time[0]
                        pending_early_entry[0] = nan
                        buy_signal = True

                        pending_buy[0] = 0.0
                        pending_buy_average[0] = nan
                        pending_buy_low[0] = nan
                        pending_buy_bar[0] = -1.0
                        pending_sell[0] = 0.0
                        pending_sell_average[0] = nan
                        pending_sell_high[0] = nan
                        pending_sell_bar[0] = -1.0

                        if not (
                            self.delete_setup == 'Primary BUY'
                            and self.bar_index == self.delete_bar_index
                        ):

                            if self.is_closed_bar:

                                pass

        # ====================================================
        # ONE COMBINED TRADE DESCRIPTION BOX
        # ====================================================

        new_trade_entry_event = (
            last_entry_bar[0] == self.bar_index
        )

        # ====================================================
        # LOT LABEL ONLY AT TRADE ENTRY
        # PROFIT / LOSS LABELS ARE DRAWN ONLY AFTER EXIT
        # ====================================================

        if (
            self.show_entry_descriptions
            and new_trade_entry_event
            and side[0] != 0.0
        ):

            is_buy = side[0] == 1.0

            trade_symbol = ''

            entry1_description_reason = (
                buy_reason if is_buy else sell_reason
            )

            entry2_description_reason = ''
            addon_zone_reason = ''

            if is_buy:

                if bullish_breakout_volume_setup or buy_reason == 'BREAKOUT + VOLUME PULLBACK':
                    entry2_description_reason = 'Breakout Pullback'

                elif bullish_engulfing:
                    entry2_description_reason = 'Engulf'

                elif bullish_hammer:
                    entry2_description_reason = 'Hammer'

                elif morning_star:
                    entry2_description_reason = 'MStar'

                elif bullish_rejection:
                    entry2_description_reason = 'Reject'

                elif bullish_break_previous:
                    entry2_description_reason = 'BrkHi'

                elif bullish_strong_body:
                    entry2_description_reason = 'Strong'

                else:
                    entry2_description_reason = 'PA'

                if support_zone:
                    entry2_description_reason += ' + Support'
                    addon_zone_reason += ' + Support'

                if bullish_ob_touch:
                    entry2_description_reason += ' + OB'
                    addon_zone_reason += ' + OB'

                if bullish_fvg_touch:
                    entry2_description_reason += ' + FVG'
                    addon_zone_reason += ' + FVG'

                if self.close[0] > ema9[0] and self.close[0] > ema20[0]:
                    entry2_description_reason += ' + EMA'

                if rsi[0] > rsi[1] and rsi[0] > 40:
                    entry2_description_reason += ' + RSI'

            else:

                if bearish_breakout_volume_setup or sell_reason == 'BREAKOUT + VOLUME PULLBACK':
                    entry2_description_reason = 'Breakout Pullback'

                elif bearish_engulfing or bearish_close_momentum:
                    entry2_description_reason = 'Engulf'

                elif bearish_shooting_star:
                    entry2_description_reason = 'SStar'

                elif evening_star:
                    entry2_description_reason = 'Evening Star'

                elif bearish_rejection:
                    entry2_description_reason = 'Reject'

                elif bearish_break_previous:
                    entry2_description_reason = 'BrkLo'

                elif bearish_strong_body:
                    entry2_description_reason = 'Strong'

                else:
                    entry2_description_reason = 'PA'

                if resistance_zone:
                    entry2_description_reason += ' + Resistance'
                    addon_zone_reason += ' + Resistance'

                if bearish_ob_touch:
                    entry2_description_reason += ' + OB'
                    addon_zone_reason += ' + OB'

                if bearish_fvg_touch:
                    entry2_description_reason += ' + FVG'
                    addon_zone_reason += ' + FVG'

                if self.close[0] < ema9[0] and self.close[0] < ema20[0]:
                    entry2_description_reason += ' + EMA'

                if rsi[0] < rsi[1] and rsi[0] < 60:
                    entry2_description_reason += ' + RSI'

            entry345_description_reason = 'PA' + addon_zone_reason

            sl_text = ' | SL ' + str(round(sl[0], 2))
            tp_text = ' | TP ' + str(round(tp[0], 2))
            lot_text = ''

            if trade_lot[0] == trade_lot[0]:
                lot_text = (
                    ' | TOTAL LOT ' + str(round(trade_lot[0], 2))
                    + ' | RISK $'
                    + str(round(trade_risk_cash[0], 2))
                )

            combined_trade_description = ''

            if entry[0] == entry[0]:

                combined_trade_description += (
                    trade_symbol + ' 1 @ ' + str(round(entry[0], 2))
                    + sl_text + tp_text + lot_text
                    + ' | Reason: ' + entry1_description_reason
                )

            if second_entry_price[0] == second_entry_price[0]:

                if combined_trade_description != '':
                    combined_trade_description += '\n'

                combined_trade_description += (
                    trade_symbol + ' 2 @ '
                    + str(round(second_entry_price[0], 2))
                    + sl_text + tp_text
                    + ' | Reason: ' + entry2_description_reason
                )

            if third_entry_price[0] == third_entry_price[0]:

                if combined_trade_description != '':
                    combined_trade_description += '\n'

                combined_trade_description += (
                    trade_symbol + ' 3 @ '
                    + str(round(third_entry_price[0], 2))
                    + sl_text + tp_text
                    + ' | Reason: ' + entry345_description_reason
                )

            if fourth_entry_price[0] == fourth_entry_price[0]:

                if combined_trade_description != '':
                    combined_trade_description += '\n'

                combined_trade_description += (
                    trade_symbol + ' 4 @ '
                    + str(round(fourth_entry_price[0], 2))
                    + sl_text + tp_text
                    + ' | Reason: ' + entry345_description_reason
                )

            if fifth_entry_price[0] == fifth_entry_price[0]:

                if combined_trade_description != '':
                    combined_trade_description += '\n'

                combined_trade_description += (
                    trade_symbol + ' 5 @ '
                    + str(round(fifth_entry_price[0], 2))
                    + sl_text + tp_text
                    + ' | Reason: ' + entry345_description_reason
                )

            if self.is_closed_bar:

                pass

        # ====================================================
        # CURRENT CHART TIMEFRAME DAILY REPORT
        # CLOSED TRADES ONLY - SPREADSHEET STYLE
        # ====================================================

        if self.show_daily_report and self.is_last_bar:

            chart_minutes = self.time_frame.to_minutes()

            timeframe_label = ''

            if chart_minutes < 60:
                timeframe_label = str(chart_minutes) + ' min'
            elif chart_minutes == 60:
                timeframe_label = '1 hour'
            elif chart_minutes % 60 == 0 and chart_minutes < 1440:
                timeframe_label = str(int(chart_minutes / 60)) + ' hours'
            elif chart_minutes >= 1440 and chart_minutes % 1440 == 0:
                timeframe_label = str(int(chart_minutes / 1440)) + ' day'
            else:
                timeframe_label = str(chart_minutes) + ' min'

            sl_count = int(report_sl[0])
            tp_count = int(report_tp[0])
            trailing_sl_count = int(report_trailing_sl[0])
            active_trades = int(report_active_trades[0])
            inactive_trades = int(report_inactive_trades[0])
            total_trades = active_trades + inactive_trades
            total_exits = sl_count + tp_count + trailing_sl_count

            win_rate = 0.0
            if total_exits > 0:
                win_rate = (tp_count / total_exits) * 100.0

            report_year = int(self.report_date / 10000)
            report_month = int((self.report_date % 10000) / 100)
            report_day = int(self.report_date % 100)

            report_day_text = str(report_day)
            report_month_text = str(report_month)

            if report_day < 10:
                report_day_text = '0' + report_day_text

            if report_month < 10:
                report_month_text = '0' + report_month_text

            date_label = (
                report_day_text + '-'
                + report_month_text + '-'
                + str(report_year)
            )

            label_width = 44
            value_width = 18

            top_border = (
                '+' + ('-' * (label_width + 2))
                + '+' + ('-' * (value_width + 2)) + '+'
            )

            header_row = (
                '| ' + '𝗞𝗦 𝗧𝗥𝗔𝗗𝗘𝗥 𝗗𝗘𝗦𝗞 - 𝗗𝗔𝗜𝗟𝗬 / 𝗠𝗢𝗡𝗧𝗛𝗟𝗬 𝗣/𝗟'.ljust(label_width) + ' | '
                + 'RESULT'.ljust(value_width) + ' |'
            )

            date_row = (
                '| ' + 'Date'.ljust(label_width) + ' | '
                + date_label.ljust(value_width) + ' |'
            )

            timeframe_row = (
                '| ' + 'Time frame'.ljust(label_width) + ' | '
                + timeframe_label.ljust(value_width) + ' |'
            )

            active_row = (
                '| ' + 'Active Trades'.ljust(label_width) + ' | '
                + str(active_trades).ljust(value_width) + ' |'
            )
            inactive_row = (
                '| ' + 'Inactive Trades'.ljust(label_width) + ' | '
                + str(inactive_trades).ljust(value_width) + ' |'
            )
            total_row = (
                '| ' + 'Total trades'.ljust(label_width) + ' | '
                + str(total_trades).ljust(value_width) + ' |'
            )

            active_pnl_row = (
                '| ' + 'Active Trade P/L'.ljust(label_width) + ' | '
                + ('$' + str(round(report_active_pnl[0], 2))).ljust(value_width) + ' |'
            )
            inactive_pnl_row = (
                '| ' + 'Inactive Trade P/L'.ljust(label_width) + ' | '
                + ('$' + str(round(report_inactive_pnl[0], 2))).ljust(value_width) + ' |'
            )

            sl_row = (
                '| ' + 'StopLoss'.ljust(label_width) + ' | '
                + str(sl_count).ljust(value_width) + ' |'
            )

            tp_row = (
                '| ' + 'Target Hit'.ljust(label_width) + ' | '
                + str(tp_count).ljust(value_width) + ' |'
            )

            trailing_sl_text = (
                str(trailing_sl_count) if trailing_sl_count > 0
                else 'No trades hit'
            )
            trailing_sl_row = (
                '| ' + 'Trailing SL Hit'.ljust(label_width) + ' | '
                + trailing_sl_text.ljust(value_width) + ' |'
            )
            win_row = (
                '| ' + 'Win Rate'.ljust(label_width) + ' | '
                + (str(int(round(win_rate))) + '%').ljust(value_width) + ' |'
            )

            rr_row = (
                '| ' + 'Risk Reward'.ljust(label_width) + ' | '
                + self.risk_reward.ljust(value_width) + ' |'
            )

            risk_mode_text = 'REDUCED 3% + 1%' if reduced_risk_mode[0] == 1.0 else 'NORMAL 5% + 2%'
            risk_mode_row = (
                '| ' + 'Current Risk Mode'.ljust(label_width) + ' | '
                + risk_mode_text.ljust(value_width) + ' |'
            )

            net_profit_row = (
                '| ' + 'Daily Net P/L'.ljust(label_width) + ' | '
                + ('$' + str(round(report_net_profit[0], 2))).ljust(value_width) + ' |'
            )

            monthly_net_profit_row = (
                '| ' + 'Monthly Net P/L'.ljust(label_width) + ' | '
                + ('$' + str(round(monthly_net_profit[0], 2))).ljust(value_width) + ' |'
            )

            report_text = (
                top_border + '\n'
                + header_row + '\n'
                + top_border + '\n'
                + date_row + '\n'
                + timeframe_row + '\n'
                + active_row + '\n'
                + inactive_row + '\n'
                + total_row + '\n'
                + active_pnl_row + '\n'
                + inactive_pnl_row + '\n'
                + sl_row + '\n'
                + tp_row + '\n'
                + trailing_sl_row + '\n'
                + win_row + '\n'
                + rr_row + '\n'
                + risk_mode_row + '\n'
                + net_profit_row + '\n'
                + monthly_net_profit_row
            )

            # Optional daily breakdown for the selected month, through the current IST date.
            if self.show_monthly_daily_breakdown:
                report_text += '\n' + top_border
                report_text += '\n| ' + 'MONTHLY DAILY NET P/L'.ljust(label_width) + ' | ' + 'AMOUNT'.ljust(value_width) + ' |'
                report_text += '\n' + top_border

                days_in_selected_month = int(
                    self._selected_report_month_end_key
                    - self._selected_report_month_start_key
                )
                current_month_day_limit = int(
                    max(
                        0.0,
                        min(
                            float(days_in_selected_month),
                            current_ist_day_key - self._selected_report_month_start_key + 1.0
                        )
                    )
                )

                month_names = [
                    '', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
                ]
                selected_month_name = month_names[report_month]

                for day_number in range(1, current_month_day_limit + 1):
                    day_profit = 0.0

                    if day_number == 1:
                        day_profit = monthly_day_01_profit[0]
                    elif day_number == 2:
                        day_profit = monthly_day_02_profit[0]
                    elif day_number == 3:
                        day_profit = monthly_day_03_profit[0]
                    elif day_number == 4:
                        day_profit = monthly_day_04_profit[0]
                    elif day_number == 5:
                        day_profit = monthly_day_05_profit[0]
                    elif day_number == 6:
                        day_profit = monthly_day_06_profit[0]
                    elif day_number == 7:
                        day_profit = monthly_day_07_profit[0]
                    elif day_number == 8:
                        day_profit = monthly_day_08_profit[0]
                    elif day_number == 9:
                        day_profit = monthly_day_09_profit[0]
                    elif day_number == 10:
                        day_profit = monthly_day_10_profit[0]
                    elif day_number == 11:
                        day_profit = monthly_day_11_profit[0]
                    elif day_number == 12:
                        day_profit = monthly_day_12_profit[0]
                    elif day_number == 13:
                        day_profit = monthly_day_13_profit[0]
                    elif day_number == 14:
                        day_profit = monthly_day_14_profit[0]
                    elif day_number == 15:
                        day_profit = monthly_day_15_profit[0]
                    elif day_number == 16:
                        day_profit = monthly_day_16_profit[0]
                    elif day_number == 17:
                        day_profit = monthly_day_17_profit[0]
                    elif day_number == 18:
                        day_profit = monthly_day_18_profit[0]
                    elif day_number == 19:
                        day_profit = monthly_day_19_profit[0]
                    elif day_number == 20:
                        day_profit = monthly_day_20_profit[0]
                    elif day_number == 21:
                        day_profit = monthly_day_21_profit[0]
                    elif day_number == 22:
                        day_profit = monthly_day_22_profit[0]
                    elif day_number == 23:
                        day_profit = monthly_day_23_profit[0]
                    elif day_number == 24:
                        day_profit = monthly_day_24_profit[0]
                    elif day_number == 25:
                        day_profit = monthly_day_25_profit[0]
                    elif day_number == 26:
                        day_profit = monthly_day_26_profit[0]
                    elif day_number == 27:
                        day_profit = monthly_day_27_profit[0]
                    elif day_number == 28:
                        day_profit = monthly_day_28_profit[0]
                    elif day_number == 29:
                        day_profit = monthly_day_29_profit[0]
                    elif day_number == 30:
                        day_profit = monthly_day_30_profit[0]
                    elif day_number == 31:
                        day_profit = monthly_day_31_profit[0]

                    daily_date_text = selected_month_name + ' ' + str(day_number)
                    daily_amount_text = '$' + str(round(day_profit, 2))
                    report_text += (
                        '\n| ' + daily_date_text.ljust(label_width)
                        + ' | ' + daily_amount_text.ljust(value_width) + ' |'
                    )

                report_text += '\n' + top_border
            else:
                report_text += '\n' + top_border

            self._daily_report_label.text = report_text
            self.chart.draw(self._daily_report_label)

        # Bar number is intentionally omitted from chart drawings.

        # ====================================================
        # PRIMARY ENTRY MARKER - RESTORED FROM ORIGINAL REPO
        # ====================================================

        marker_price = nan

        if (
            buy_signal
            and not (
                self.delete_setup == 'Primary BUY'
                and self.bar_index == self.delete_bar_index
            )
        ):
            marker_price = self.low[0] - entry_marker_offset

        elif (
            sell_signal
            and not (
                self.delete_setup == 'Primary SELL'
                and self.bar_index == self.delete_bar_index
            )
        ):
            marker_price = self.high[0] + entry_marker_offset

        marker_color = (
            color.RED
            if buy_signal or sell_signal
            else color.TRANSPARENT
        )

        # ====================================================
        # VISUAL TRADE LEVELS
        # Keep the planned Entry / SL / TP visible from the setup
        # candle while the order is pending. This is display-only;
        # internal active-trade calculations continue using entry/sl/tp.
        # ====================================================

        plot_entry_value = entry[0]
        plot_sl_value = sl[0]
        plot_tp_value = tp[0]

        if side[0] != 0.0:
            plot_entry_value = midpoint_master_entry[0]
            plot_sl_value = sl[0]
            plot_tp_value = tp[0]

        # ====================================================
        # OUTPUT
        # ====================================================

        return (
            ema9[0],
            ema20[0],
            ema50[0],
            ema200[0],

            plot_entry_value,
            second_entry_price[0],
            third_entry_price[0],
            fourth_entry_price[0],
            fifth_entry_price[0],

            plot_sl_value,
            plot_tp_value,

            plot.Fill(),
            plot.Fill(),

            plot.Marker(
                value=marker_price,
                color=marker_color
            )
        )
 + str(round(result_amount, 2)),
                            AbsolutePosition(self.time[0], tp[0]),
                            font_size=9, text_color=color.BLACK,
                            bg_color=color.TRANSPARENT
                        ))
                    elif report_hit_sl:
                        exit_label = 'TRAIL -

                    if current_ist_day_key == risk_day_key[0]:
                        daily_realized_pnl[0] = daily_realized_pnl[0] + realized_pnl
                        daily_loss_threshold = daily_start_balance[0] * 0.30
                        if daily_realized_pnl[0] <= -daily_loss_threshold:
                            reduced_risk_mode[0] = 1.0
                        elif daily_realized_pnl[0] >= 0.0:
                            reduced_risk_mode[0] = 0.0

                    if current_ist_day_key == self._selected_report_day_key:
                        if report_hit_trailing_sl:
                            report_trailing_sl[0] = report_trailing_sl[0] + 1.0
                        elif report_hit_sl:
                            report_sl[0] = report_sl[0] + 1.0
                        elif report_hit_tp:
                            report_tp[0] = report_tp[0] + 1.0
                        report_net_profit[0] = report_net_profit[0] + realized_pnl
                        report_active_pnl[0] = report_active_pnl[0] + realized_pnl

                    if (
                        current_ist_day_key >= self._selected_report_month_start_key
                        and current_ist_day_key < self._selected_report_month_end_key
                    ):
                        monthly_net_profit[0] = monthly_net_profit[0] + realized_pnl
                    if current_ist_day_key == self._selected_report_month_start_key + 0.0:
                        monthly_day_01_profit[0] = monthly_day_01_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 1.0:
                        monthly_day_02_profit[0] = monthly_day_02_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 2.0:
                        monthly_day_03_profit[0] = monthly_day_03_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 3.0:
                        monthly_day_04_profit[0] = monthly_day_04_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 4.0:
                        monthly_day_05_profit[0] = monthly_day_05_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 5.0:
                        monthly_day_06_profit[0] = monthly_day_06_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 6.0:
                        monthly_day_07_profit[0] = monthly_day_07_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 7.0:
                        monthly_day_08_profit[0] = monthly_day_08_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 8.0:
                        monthly_day_09_profit[0] = monthly_day_09_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 9.0:
                        monthly_day_10_profit[0] = monthly_day_10_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 10.0:
                        monthly_day_11_profit[0] = monthly_day_11_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 11.0:
                        monthly_day_12_profit[0] = monthly_day_12_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 12.0:
                        monthly_day_13_profit[0] = monthly_day_13_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 13.0:
                        monthly_day_14_profit[0] = monthly_day_14_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 14.0:
                        monthly_day_15_profit[0] = monthly_day_15_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 15.0:
                        monthly_day_16_profit[0] = monthly_day_16_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 16.0:
                        monthly_day_17_profit[0] = monthly_day_17_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 17.0:
                        monthly_day_18_profit[0] = monthly_day_18_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 18.0:
                        monthly_day_19_profit[0] = monthly_day_19_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 19.0:
                        monthly_day_20_profit[0] = monthly_day_20_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 20.0:
                        monthly_day_21_profit[0] = monthly_day_21_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 21.0:
                        monthly_day_22_profit[0] = monthly_day_22_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 22.0:
                        monthly_day_23_profit[0] = monthly_day_23_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 23.0:
                        monthly_day_24_profit[0] = monthly_day_24_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 24.0:
                        monthly_day_25_profit[0] = monthly_day_25_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 25.0:
                        monthly_day_26_profit[0] = monthly_day_26_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 26.0:
                        monthly_day_27_profit[0] = monthly_day_27_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 27.0:
                        monthly_day_28_profit[0] = monthly_day_28_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 28.0:
                        monthly_day_29_profit[0] = monthly_day_29_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 29.0:
                        monthly_day_30_profit[0] = monthly_day_30_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 30.0:
                        monthly_day_31_profit[0] = monthly_day_31_profit[0] + realized_pnl

                entry[0] = nan
                early_leg_entry[0] = nan
                midpoint_master_entry[0] = nan
                early_leg_lot[0] = nan
                mid_leg_lot[0] = nan
                mid_leg_active[0] = 0.0
                early_leg_closed[0] = 0.0
                pending_mid_entry[0] = nan
                pending_early_entry[0] = nan
                pending_trade_side[0] = 0.0
                pending_trade_entry[0] = nan
                pending_trade_sl[0] = nan
                pending_trade_tp[0] = nan
                pending_trade_lot[0] = nan
                pending_trade_risk_cash[0] = nan
                pending_trade_setup_day[0] = nan
                pending_trade_setup_bar[0] = -1.0
                second_entry_price[0] = nan
                third_entry_price[0] = nan
                fourth_entry_price[0] = nan
                fifth_entry_price[0] = nan
                sl[0] = nan
                tp[0] = nan
                side[0] = 0.0
                trade_lot[0] = nan
                trade_risk_cash[0] = nan
                original_risk_distance[0] = nan
                favorable_extreme[0] = nan
                trail_candidate[0] = nan
                trail_confirm_count[0] = 0.0
                trail_stage[0] = 0.0
                trail_last_update_bar[0] = -1.0
                entry_count[0] = 0.0
                last_entry_bar[0] = -1.0
                last_entry_price[0] = nan
                entry_label_time[0] = nan
                early_exit_warned[0] = 0.0
                pending_buy[0] = 0.0
                pending_buy_average[0] = nan
                pending_buy_low[0] = nan
                pending_buy_bar[0] = -1.0
                pending_sell[0] = 0.0
                pending_sell_average[0] = nan
                pending_sell_high[0] = nan
                pending_sell_bar[0] = -1.0
                trade_exited = True

            # ================================================
            # ADAPTIVE HYBRID TRAILING (M1, CLOSED CANDLES ONLY)
            # ================================================
            # This is a chart-side simulated stop line. Exness Indie custom
            # indicators cannot modify an actual broker position's SL.
            if (
                self.adaptive_trailing_enabled
                and self._is_m1_chart
                and side[0] != 0.0
                and mid_leg_active[0] == 1.0
                and self.bar_index > last_entry_bar[0]
                and original_risk_distance[0] > 0.0
                and not trade_exited
            ):
                is_buy_trail = side[0] == 1.0
                entry[0] = midpoint_master_entry[0]
                risk_unit = original_risk_distance[0]
                atr_value = atr14[0]
                adx_value = adx14[0]
                minus_value = minus_di[0]
                plus_value = plus_di[0]
                proposed_sl = sl[0]

                # Track the best favourable excursion since the simulated entry.
                # Declare shared-scope values before the BUY/SELL branches.
                favourable_move = 0.0
                target_distance = 0.0
                if is_buy_trail:
                    if isnan(favorable_extreme[0]):
                        favorable_extreme[0] = self.high[0]
                    else:
                        favorable_extreme[0] = max(favorable_extreme[0], self.high[0])
                    favourable_move = favorable_extreme[0] - entry[0]
                    target_distance = tp[0] - entry[0]
                else:
                    if isnan(favorable_extreme[0]):
                        favorable_extreme[0] = self.low[0]
                    else:
                        favorable_extreme[0] = min(favorable_extreme[0], self.low[0])
                    favourable_move = entry[0] - favorable_extreme[0]
                    target_distance = entry[0] - tp[0]

                r_progress = favourable_move / risk_unit if risk_unit > 0.0 else 0.0
                tp_progress = (
                    favourable_move / target_distance
                    if target_distance > 0.0 else 0.0
                )

                # 1R: break-even (optional user-supplied cost buffer).
                if r_progress >= 1.0:
                    if is_buy_trail:
                        proposed_sl = max(proposed_sl, entry[0] + self.break_even_buffer)
                    else:
                        proposed_sl = min(proposed_sl, entry[0] - self.break_even_buffer)

                # TP progress locks are based on the ORIGINAL risk distance.
                if tp_progress >= 0.95:
                    lock_price = 0.60 * risk_unit
                    if is_buy_trail:
                        proposed_sl = max(proposed_sl, entry[0] + lock_price)
                    else:
                        proposed_sl = min(proposed_sl, entry[0] - lock_price)
                elif tp_progress >= 0.85:
                    lock_price = 0.30 * risk_unit
                    if is_buy_trail:
                        proposed_sl = max(proposed_sl, entry[0] + lock_price)
                    else:
                        proposed_sl = min(proposed_sl, entry[0] - lock_price)

                # Swing structure + ATR trailing begins after 1.4R.
                if r_progress >= 1.4 and not isnan(atr_value) and atr_value > 0.0:
                    strong_buy_trend = (
                        adx_value >= 25.0
                        and plus_value > minus_value
                        and trail_ema9[0] > trail_ema21[0]
                    )
                    strong_sell_trend = (
                        adx_value >= 25.0
                        and minus_value > plus_value
                        and trail_ema9[0] < trail_ema21[0]
                    )
                    atr_multiplier = 1.5 if (
                        (is_buy_trail and strong_buy_trend)
                        or ((not is_buy_trail) and strong_sell_trend)
                    ) else 1.0
                    atr_buffer = atr_value * atr_multiplier

                    if is_buy_trail:
                        # Confirmed pivot low: two bars on either side.
                        confirmed_swing_low = (
                            self.low[2] < self.low[1]
                            and self.low[2] < self.low[0]
                            and self.low[2] <= self.low[3]
                            and self.low[2] <= self.low[4]
                        )
                        if confirmed_swing_low:
                            swing_candidate = self.low[2] - atr_buffer
                            if swing_candidate > proposed_sl and swing_candidate < self.close[0]:
                                proposed_sl = max(proposed_sl, swing_candidate)

                        # Three bearish closes are a confirmed adverse reaction.
                        bearish_three = (
                            self.close[0] < self.close[1]
                            and self.close[1] < self.close[2]
                            and self.close[0] < trail_ema9[0]
                        )
                        if bearish_three:
                            reaction_candidate = min([
                                self.low[0], self.low[1], self.low[2]
                            ]) - atr_value
                            if reaction_candidate > proposed_sl and reaction_candidate < self.close[0]:
                                proposed_sl = max(proposed_sl, reaction_candidate)
                    else:
                        # Confirmed pivot high: two bars on either side.
                        confirmed_swing_high = (
                            self.high[2] > self.high[1]
                            and self.high[2] > self.high[0]
                            and self.high[2] >= self.high[3]
                            and self.high[2] >= self.high[4]
                        )
                        if confirmed_swing_high:
                            swing_candidate = self.high[2] + atr_buffer
                            if swing_candidate < proposed_sl and swing_candidate > self.close[0]:
                                proposed_sl = min(proposed_sl, swing_candidate)

                        # Three bullish closes are a confirmed adverse reaction.
                        bullish_three = (
                            self.close[0] > self.close[1]
                            and self.close[1] > self.close[2]
                            and self.close[0] > trail_ema9[0]
                        )
                        if bullish_three:
                            reaction_candidate = max([
                                self.high[0], self.high[1], self.high[2]
                            ]) + atr_value
                            if reaction_candidate < proposed_sl and reaction_candidate > self.close[0]:
                                proposed_sl = min(proposed_sl, reaction_candidate)

                # Candidate must improve protection and remain beyond the close.
                candidate_is_valid = (
                    proposed_sl > sl[0] and proposed_sl < self.close[0]
                    if is_buy_trail else
                    proposed_sl < sl[0] and proposed_sl > self.close[0]
                )

                # Require 3 consecutive completed M1 closes to confirm the same
                # or a more protective candidate. Never loosen an existing stop.
                if candidate_is_valid:
                    if is_buy_trail:
                        if isnan(trail_candidate[0]) or proposed_sl > trail_candidate[0]:
                            trail_candidate[0] = proposed_sl
                            trail_confirm_count[0] = 0.0
                    else:
                        if isnan(trail_candidate[0]) or proposed_sl < trail_candidate[0]:
                            trail_candidate[0] = proposed_sl
                            trail_confirm_count[0] = 0.0

                if not isnan(trail_candidate[0]):
                    candidate_still_safe = (
                        self.close[0] > trail_candidate[0]
                        if is_buy_trail else
                        self.close[0] < trail_candidate[0]
                    )
                    if candidate_still_safe:
                        trail_confirm_count[0] = trail_confirm_count[0] + 1.0
                    else:
                        trail_candidate[0] = nan
                        trail_confirm_count[0] = 0.0

                if (
                    not isnan(trail_candidate[0])
                    and trail_confirm_count[0] >= 3.0
                    and (
                        (is_buy_trail and trail_candidate[0] > sl[0])
                        or ((not is_buy_trail) and trail_candidate[0] < sl[0])
                    )
                ):
                    sl[0] = trail_candidate[0]
                    trail_last_update_bar[0] = float(self.bar_index)
                    trail_confirm_count[0] = 0.0
                    trail_candidate[0] = nan

                    # Draw each label inside its own branch. Indie variables
                    # declared inside an indented branch are not visible outside it.
                    if tp_progress >= 0.95:
                        trail_stage[0] = 3.0
                        self.chart.draw(
                            LabelAbs(
                                'ADAPTIVE SL: LOCK 0.60R',
                                AbsolutePosition(self.time[0], sl[0]),
                                font_size=9,
                                text_color=color.BLACK,
                                bg_color=color.TRANSPARENT
                            )
                        )
                    elif tp_progress >= 0.85:
                        trail_stage[0] = 2.0
                        self.chart.draw(
                            LabelAbs(
                                'ADAPTIVE SL: LOCK 0.30R',
                                AbsolutePosition(self.time[0], sl[0]),
                                font_size=9,
                                text_color=color.BLACK,
                                bg_color=color.TRANSPARENT
                            )
                        )
                    elif r_progress >= 1.0:
                        trail_stage[0] = 1.0
                        self.chart.draw(
                            LabelAbs(
                                'ADAPTIVE SL: BREAK EVEN / TRAIL',
                                AbsolutePosition(self.time[0], sl[0]),
                                font_size=9,
                                text_color=color.BLACK,
                                bg_color=color.TRANSPARENT
                            )
                        )
                    else:
                        trail_stage[0] = 4.0
                        self.chart.draw(
                            LabelAbs(
                                'ADAPTIVE SL: STRUCTURE TRAIL',
                                AbsolutePosition(self.time[0], sl[0]),
                                font_size=9,
                                text_color=color.BLACK,
                                bg_color=color.TRANSPARENT
                            )
                        )

                entry[0] = early_leg_entry[0]

            # ================================================
            # EARLY EXIT WARNING
            # ================================================

            if side[0] == 1.0 and early_exit_warned[0] == 0.0:

                buy_failure_score = 0

                if self.close[0] < ema20[0] and ema20[0] < ema50[0]:
                    buy_failure_score += 1

                if htf_sell:
                    buy_failure_score += 1

                if rsi[0] < 45 and rsi[0] < rsi[1]:
                    buy_failure_score += 1

                if bearish_price_action:
                    buy_failure_score += 1

                if buy_failure_score >= 3:

                    early_exit_warned[0] = 1.0

                    if self.is_closed_bar:

                        pass

            elif side[0] == -1.0 and early_exit_warned[0] == 0.0:

                sell_failure_score = 0

                if self.close[0] > ema20[0] and ema20[0] > ema50[0]:
                    sell_failure_score += 1

                if htf_buy:
                    sell_failure_score += 1

                if rsi[0] > 55 and rsi[0] > rsi[1]:
                    sell_failure_score += 1

                if bullish_price_action:
                    sell_failure_score += 1

                if sell_failure_score >= 3:

                    early_exit_warned[0] = 1.0

                    if self.is_closed_bar:

                        pass

            # ================================================
            # ADD-ON ENTRIES 2 TO 5
            # ================================================

            if (
                side[0] != 0.0
                and entry_count[0] >= 1.0
                and entry_count[0] < 5.0
                and self.bar_index > last_entry_bar[0]
            ):

                is_buy_side = side[0] == 1.0

                add_ok = False

                if is_buy_side:

                    add_ok = (
                        candidate_entry_price < last_entry_price[0]
                        and bullish_price_action
                        and buy_add_location
                        and buy_add_score >= 4
                    )

                else:

                    add_ok = (
                        candidate_entry_price > last_entry_price[0]
                        and bearish_price_action
                        and sell_add_location
                        and sell_add_score >= 4
                    )

                if add_ok:

                    new_count = entry_count[0] + 1.0

                    entry_count[0] = new_count
                    last_entry_bar[0] = float(self.bar_index)
                    last_entry_price[0] = candidate_entry_price

                    add_name = 'Second'
                    add_color = color.BLACK

                    if new_count == 2.0:
                        second_entry_price[0] = candidate_entry_price

                    elif new_count == 3.0:
                        third_entry_price[0] = candidate_entry_price
                        add_name = 'Third'
                        add_color = color.FUCHSIA

                    elif new_count == 4.0:
                        fourth_entry_price[0] = candidate_entry_price
                        add_name = 'Fourth'
                        add_color = color.YELLOW

                    else:
                        fifth_entry_price[0] = candidate_entry_price
                        add_name = 'Fifth'
                        add_color = color.PURPLE

                    add_setup_name = add_name + (
                        ' BUY' if is_buy_side else ' SELL'
                    )

                    if not (
                        self.delete_setup == add_setup_name
                        and self.bar_index == self.delete_bar_index
                    ):

                        if is_buy_side:

                            if self.is_closed_bar:

                                pass

                        else:

                            if self.is_closed_bar:

                                pass

            # ================================================
            # ARM NEW BREAKOUT PULLBACK SETUPS
            # ================================================

            if side[0] == 0.0 and not trade_exited:

                if bullish_breakout_volume_setup:

                    pending_buy[0] = 1.0
                    pending_buy_average[0] = (
                        self.high[0] + self.low[0]
                    ) / 2.0
                    pending_buy_low[0] = self.low[0]
                    pending_buy_bar[0] = float(self.bar_index)

                    pending_sell[0] = 0.0
                    pending_sell_average[0] = nan
                    pending_sell_high[0] = nan
                    pending_sell_bar[0] = -1.0

                elif bearish_breakout_volume_setup:

                    pending_sell[0] = 1.0
                    pending_sell_average[0] = (
                        self.high[0] + self.low[0]
                    ) / 2.0
                    pending_sell_high[0] = self.high[0]
                    pending_sell_bar[0] = float(self.bar_index)

                    pending_buy[0] = 0.0
                    pending_buy_average[0] = nan
                    pending_buy_low[0] = nan
                    pending_buy_bar[0] = -1.0

            # ================================================
            # VALIDATE / EXPIRE PENDING BUY SETUP
            # ================================================

            if (
                pending_buy[0] == 1.0
                and self.bar_index > pending_buy_bar[0]
            ):

                buy_pending_age = (
                    self.bar_index - pending_buy_bar[0]
                )

                if (
                    buy_pending_age > 10.0
                    or self.close[0] < pending_buy_low[0]
                ):

                    pending_buy[0] = 0.0
                    pending_buy_average[0] = nan
                    pending_buy_low[0] = nan
                    pending_buy_bar[0] = -1.0

            # ================================================
            # VALIDATE / EXPIRE PENDING SELL SETUP
            # ================================================

            if (
                pending_sell[0] == 1.0
                and self.bar_index > pending_sell_bar[0]
            ):

                sell_pending_age = (
                    self.bar_index - pending_sell_bar[0]
                )

                if (
                    sell_pending_age > 10.0
                    or self.close[0] > pending_sell_high[0]
                ):

                    pending_sell[0] = 0.0
                    pending_sell_average[0] = nan
                    pending_sell_high[0] = nan
                    pending_sell_bar[0] = -1.0

            # ================================================
            # CHECK BUY PULLBACK ENTRY
            # ================================================

            buy_breakout_pullback_ready = False
            buy_breakout_entry_price = nan

            bullish_pullback_confirmation = (
                self.close[0] > self.open[0]
                and (
                    bullish_rejection
                    or bullish_engulfing
                    or bullish_hammer
                    or bullish_close_momentum
                )
            )

            if (
                pending_buy[0] == 1.0
                and self.bar_index > pending_buy_bar[0]
                and bullish_pullback_confirmation
            ):

                buy_average_touched = (
                    self.low[0] <= pending_buy_average[0]
                    and self.close[0] > pending_buy_average[0]
                )

                buy_bottom_touched = (
                    self.low[0] <= pending_buy_low[0]
                    and self.close[0] > pending_buy_low[0]
                )

                if buy_average_touched:

                    buy_breakout_pullback_ready = True
                    buy_breakout_entry_price = pending_buy_average[0]

                elif buy_bottom_touched:

                    buy_breakout_pullback_ready = True
                    buy_breakout_entry_price = pending_buy_low[0]

            # ================================================
            # CHECK SELL PULLBACK ENTRY
            # ================================================

            sell_breakout_pullback_ready = False
            sell_breakout_entry_price = nan

            bearish_pullback_confirmation = (
                self.close[0] < self.open[0]
                and (
                    bearish_rejection
                    or bearish_engulfing
                    or bearish_shooting_star
                    or bearish_close_momentum
                )
            )

            if (
                pending_sell[0] == 1.0
                and self.bar_index > pending_sell_bar[0]
                and bearish_pullback_confirmation
            ):

                sell_average_touched = (
                    self.high[0] >= pending_sell_average[0]
                    and self.close[0] < pending_sell_average[0]
                )

                sell_top_touched = (
                    self.high[0] >= pending_sell_high[0]
                    and self.close[0] < pending_sell_high[0]
                )

                if sell_average_touched:

                    sell_breakout_pullback_ready = True
                    sell_breakout_entry_price = pending_sell_average[0]

                elif sell_top_touched:

                    sell_breakout_pullback_ready = True
                    sell_breakout_entry_price = pending_sell_high[0]

            # ================================================
            # DYNAMIC DAILY RISK BUDGET
            # ================================================

            if reduced_risk_mode[0] == 1.0:
                total_risk_percent = reduced_risk_percent
            else:
                total_risk_percent = normal_risk_percent

            risk_budget_cash = (
                self.account_capital * total_risk_percent / 100.0
            )

            # Independent original-midpoint setup counter.
            # Resolve every outstanding setup independently before arming this bar's setup.
            # SL/TP wins over midpoint if both are touched on the same candle.
            if self.is_closed_bar:
                if count_1_side[0] != 0.0 and self.bar_index > count_1_bar[0]:
                    count_1_entry_touched = (
                        self.low[0] <= count_1_entry[0]
                        if count_1_side[0] == 1.0 else
                        self.high[0] >= count_1_entry[0]
                    )
                    count_1_sl_touched = (
                        self.low[0] <= count_1_sl[0]
                        if count_1_side[0] == 1.0 else
                        self.high[0] >= count_1_sl[0]
                    )
                    count_1_tp_touched = (
                        self.high[0] >= count_1_tp[0]
                        if count_1_side[0] == 1.0 else
                        self.low[0] <= count_1_tp[0]
                    )
                    if count_1_sl_touched or count_1_tp_touched:
                        if count_1_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_1_side[0] = 0.0
                        count_1_entry[0] = nan
                        count_1_sl[0] = nan
                        count_1_tp[0] = nan
                        count_1_day[0] = nan
                        count_1_bar[0] = -1.0
                    elif count_1_entry_touched:
                        if count_1_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_1_side[0] = 0.0
                        count_1_entry[0] = nan
                        count_1_sl[0] = nan
                        count_1_tp[0] = nan
                        count_1_day[0] = nan
                        count_1_bar[0] = -1.0

                if count_2_side[0] != 0.0 and self.bar_index > count_2_bar[0]:
                    count_2_entry_touched = (
                        self.low[0] <= count_2_entry[0]
                        if count_2_side[0] == 1.0 else
                        self.high[0] >= count_2_entry[0]
                    )
                    count_2_sl_touched = (
                        self.low[0] <= count_2_sl[0]
                        if count_2_side[0] == 1.0 else
                        self.high[0] >= count_2_sl[0]
                    )
                    count_2_tp_touched = (
                        self.high[0] >= count_2_tp[0]
                        if count_2_side[0] == 1.0 else
                        self.low[0] <= count_2_tp[0]
                    )
                    if count_2_sl_touched or count_2_tp_touched:
                        if count_2_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_2_side[0] = 0.0
                        count_2_entry[0] = nan
                        count_2_sl[0] = nan
                        count_2_tp[0] = nan
                        count_2_day[0] = nan
                        count_2_bar[0] = -1.0
                    elif count_2_entry_touched:
                        if count_2_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_2_side[0] = 0.0
                        count_2_entry[0] = nan
                        count_2_sl[0] = nan
                        count_2_tp[0] = nan
                        count_2_day[0] = nan
                        count_2_bar[0] = -1.0

                if count_3_side[0] != 0.0 and self.bar_index > count_3_bar[0]:
                    count_3_entry_touched = (
                        self.low[0] <= count_3_entry[0]
                        if count_3_side[0] == 1.0 else
                        self.high[0] >= count_3_entry[0]
                    )
                    count_3_sl_touched = (
                        self.low[0] <= count_3_sl[0]
                        if count_3_side[0] == 1.0 else
                        self.high[0] >= count_3_sl[0]
                    )
                    count_3_tp_touched = (
                        self.high[0] >= count_3_tp[0]
                        if count_3_side[0] == 1.0 else
                        self.low[0] <= count_3_tp[0]
                    )
                    if count_3_sl_touched or count_3_tp_touched:
                        if count_3_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_3_side[0] = 0.0
                        count_3_entry[0] = nan
                        count_3_sl[0] = nan
                        count_3_tp[0] = nan
                        count_3_day[0] = nan
                        count_3_bar[0] = -1.0
                    elif count_3_entry_touched:
                        if count_3_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_3_side[0] = 0.0
                        count_3_entry[0] = nan
                        count_3_sl[0] = nan
                        count_3_tp[0] = nan
                        count_3_day[0] = nan
                        count_3_bar[0] = -1.0

                if count_4_side[0] != 0.0 and self.bar_index > count_4_bar[0]:
                    count_4_entry_touched = (
                        self.low[0] <= count_4_entry[0]
                        if count_4_side[0] == 1.0 else
                        self.high[0] >= count_4_entry[0]
                    )
                    count_4_sl_touched = (
                        self.low[0] <= count_4_sl[0]
                        if count_4_side[0] == 1.0 else
                        self.high[0] >= count_4_sl[0]
                    )
                    count_4_tp_touched = (
                        self.high[0] >= count_4_tp[0]
                        if count_4_side[0] == 1.0 else
                        self.low[0] <= count_4_tp[0]
                    )
                    if count_4_sl_touched or count_4_tp_touched:
                        if count_4_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_4_side[0] = 0.0
                        count_4_entry[0] = nan
                        count_4_sl[0] = nan
                        count_4_tp[0] = nan
                        count_4_day[0] = nan
                        count_4_bar[0] = -1.0
                    elif count_4_entry_touched:
                        if count_4_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_4_side[0] = 0.0
                        count_4_entry[0] = nan
                        count_4_sl[0] = nan
                        count_4_tp[0] = nan
                        count_4_day[0] = nan
                        count_4_bar[0] = -1.0

                if count_5_side[0] != 0.0 and self.bar_index > count_5_bar[0]:
                    count_5_entry_touched = (
                        self.low[0] <= count_5_entry[0]
                        if count_5_side[0] == 1.0 else
                        self.high[0] >= count_5_entry[0]
                    )
                    count_5_sl_touched = (
                        self.low[0] <= count_5_sl[0]
                        if count_5_side[0] == 1.0 else
                        self.high[0] >= count_5_sl[0]
                    )
                    count_5_tp_touched = (
                        self.high[0] >= count_5_tp[0]
                        if count_5_side[0] == 1.0 else
                        self.low[0] <= count_5_tp[0]
                    )
                    if count_5_sl_touched or count_5_tp_touched:
                        if count_5_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_5_side[0] = 0.0
                        count_5_entry[0] = nan
                        count_5_sl[0] = nan
                        count_5_tp[0] = nan
                        count_5_day[0] = nan
                        count_5_bar[0] = -1.0
                    elif count_5_entry_touched:
                        if count_5_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_5_side[0] = 0.0
                        count_5_entry[0] = nan
                        count_5_sl[0] = nan
                        count_5_tp[0] = nan
                        count_5_day[0] = nan
                        count_5_bar[0] = -1.0

                if count_6_side[0] != 0.0 and self.bar_index > count_6_bar[0]:
                    count_6_entry_touched = (
                        self.low[0] <= count_6_entry[0]
                        if count_6_side[0] == 1.0 else
                        self.high[0] >= count_6_entry[0]
                    )
                    count_6_sl_touched = (
                        self.low[0] <= count_6_sl[0]
                        if count_6_side[0] == 1.0 else
                        self.high[0] >= count_6_sl[0]
                    )
                    count_6_tp_touched = (
                        self.high[0] >= count_6_tp[0]
                        if count_6_side[0] == 1.0 else
                        self.low[0] <= count_6_tp[0]
                    )
                    if count_6_sl_touched or count_6_tp_touched:
                        if count_6_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_6_side[0] = 0.0
                        count_6_entry[0] = nan
                        count_6_sl[0] = nan
                        count_6_tp[0] = nan
                        count_6_day[0] = nan
                        count_6_bar[0] = -1.0
                    elif count_6_entry_touched:
                        if count_6_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_6_side[0] = 0.0
                        count_6_entry[0] = nan
                        count_6_sl[0] = nan
                        count_6_tp[0] = nan
                        count_6_day[0] = nan
                        count_6_bar[0] = -1.0

                if count_7_side[0] != 0.0 and self.bar_index > count_7_bar[0]:
                    count_7_entry_touched = (
                        self.low[0] <= count_7_entry[0]
                        if count_7_side[0] == 1.0 else
                        self.high[0] >= count_7_entry[0]
                    )
                    count_7_sl_touched = (
                        self.low[0] <= count_7_sl[0]
                        if count_7_side[0] == 1.0 else
                        self.high[0] >= count_7_sl[0]
                    )
                    count_7_tp_touched = (
                        self.high[0] >= count_7_tp[0]
                        if count_7_side[0] == 1.0 else
                        self.low[0] <= count_7_tp[0]
                    )
                    if count_7_sl_touched or count_7_tp_touched:
                        if count_7_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_7_side[0] = 0.0
                        count_7_entry[0] = nan
                        count_7_sl[0] = nan
                        count_7_tp[0] = nan
                        count_7_day[0] = nan
                        count_7_bar[0] = -1.0
                    elif count_7_entry_touched:
                        if count_7_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_7_side[0] = 0.0
                        count_7_entry[0] = nan
                        count_7_sl[0] = nan
                        count_7_tp[0] = nan
                        count_7_day[0] = nan
                        count_7_bar[0] = -1.0

                if count_8_side[0] != 0.0 and self.bar_index > count_8_bar[0]:
                    count_8_entry_touched = (
                        self.low[0] <= count_8_entry[0]
                        if count_8_side[0] == 1.0 else
                        self.high[0] >= count_8_entry[0]
                    )
                    count_8_sl_touched = (
                        self.low[0] <= count_8_sl[0]
                        if count_8_side[0] == 1.0 else
                        self.high[0] >= count_8_sl[0]
                    )
                    count_8_tp_touched = (
                        self.high[0] >= count_8_tp[0]
                        if count_8_side[0] == 1.0 else
                        self.low[0] <= count_8_tp[0]
                    )
                    if count_8_sl_touched or count_8_tp_touched:
                        if count_8_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_8_side[0] = 0.0
                        count_8_entry[0] = nan
                        count_8_sl[0] = nan
                        count_8_tp[0] = nan
                        count_8_day[0] = nan
                        count_8_bar[0] = -1.0
                    elif count_8_entry_touched:
                        if count_8_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_8_side[0] = 0.0
                        count_8_entry[0] = nan
                        count_8_sl[0] = nan
                        count_8_tp[0] = nan
                        count_8_day[0] = nan
                        count_8_bar[0] = -1.0

                if count_9_side[0] != 0.0 and self.bar_index > count_9_bar[0]:
                    count_9_entry_touched = (
                        self.low[0] <= count_9_entry[0]
                        if count_9_side[0] == 1.0 else
                        self.high[0] >= count_9_entry[0]
                    )
                    count_9_sl_touched = (
                        self.low[0] <= count_9_sl[0]
                        if count_9_side[0] == 1.0 else
                        self.high[0] >= count_9_sl[0]
                    )
                    count_9_tp_touched = (
                        self.high[0] >= count_9_tp[0]
                        if count_9_side[0] == 1.0 else
                        self.low[0] <= count_9_tp[0]
                    )
                    if count_9_sl_touched or count_9_tp_touched:
                        if count_9_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_9_side[0] = 0.0
                        count_9_entry[0] = nan
                        count_9_sl[0] = nan
                        count_9_tp[0] = nan
                        count_9_day[0] = nan
                        count_9_bar[0] = -1.0
                    elif count_9_entry_touched:
                        if count_9_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_9_side[0] = 0.0
                        count_9_entry[0] = nan
                        count_9_sl[0] = nan
                        count_9_tp[0] = nan
                        count_9_day[0] = nan
                        count_9_bar[0] = -1.0

                if count_10_side[0] != 0.0 and self.bar_index > count_10_bar[0]:
                    count_10_entry_touched = (
                        self.low[0] <= count_10_entry[0]
                        if count_10_side[0] == 1.0 else
                        self.high[0] >= count_10_entry[0]
                    )
                    count_10_sl_touched = (
                        self.low[0] <= count_10_sl[0]
                        if count_10_side[0] == 1.0 else
                        self.high[0] >= count_10_sl[0]
                    )
                    count_10_tp_touched = (
                        self.high[0] >= count_10_tp[0]
                        if count_10_side[0] == 1.0 else
                        self.low[0] <= count_10_tp[0]
                    )
                    if count_10_sl_touched or count_10_tp_touched:
                        if count_10_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_10_side[0] = 0.0
                        count_10_entry[0] = nan
                        count_10_sl[0] = nan
                        count_10_tp[0] = nan
                        count_10_day[0] = nan
                        count_10_bar[0] = -1.0
                    elif count_10_entry_touched:
                        if count_10_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_10_side[0] = 0.0
                        count_10_entry[0] = nan
                        count_10_sl[0] = nan
                        count_10_tp[0] = nan
                        count_10_day[0] = nan
                        count_10_bar[0] = -1.0

                if count_11_side[0] != 0.0 and self.bar_index > count_11_bar[0]:
                    count_11_entry_touched = (
                        self.low[0] <= count_11_entry[0]
                        if count_11_side[0] == 1.0 else
                        self.high[0] >= count_11_entry[0]
                    )
                    count_11_sl_touched = (
                        self.low[0] <= count_11_sl[0]
                        if count_11_side[0] == 1.0 else
                        self.high[0] >= count_11_sl[0]
                    )
                    count_11_tp_touched = (
                        self.high[0] >= count_11_tp[0]
                        if count_11_side[0] == 1.0 else
                        self.low[0] <= count_11_tp[0]
                    )
                    if count_11_sl_touched or count_11_tp_touched:
                        if count_11_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_11_side[0] = 0.0
                        count_11_entry[0] = nan
                        count_11_sl[0] = nan
                        count_11_tp[0] = nan
                        count_11_day[0] = nan
                        count_11_bar[0] = -1.0
                    elif count_11_entry_touched:
                        if count_11_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_11_side[0] = 0.0
                        count_11_entry[0] = nan
                        count_11_sl[0] = nan
                        count_11_tp[0] = nan
                        count_11_day[0] = nan
                        count_11_bar[0] = -1.0

                if count_12_side[0] != 0.0 and self.bar_index > count_12_bar[0]:
                    count_12_entry_touched = (
                        self.low[0] <= count_12_entry[0]
                        if count_12_side[0] == 1.0 else
                        self.high[0] >= count_12_entry[0]
                    )
                    count_12_sl_touched = (
                        self.low[0] <= count_12_sl[0]
                        if count_12_side[0] == 1.0 else
                        self.high[0] >= count_12_sl[0]
                    )
                    count_12_tp_touched = (
                        self.high[0] >= count_12_tp[0]
                        if count_12_side[0] == 1.0 else
                        self.low[0] <= count_12_tp[0]
                    )
                    if count_12_sl_touched or count_12_tp_touched:
                        if count_12_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_12_side[0] = 0.0
                        count_12_entry[0] = nan
                        count_12_sl[0] = nan
                        count_12_tp[0] = nan
                        count_12_day[0] = nan
                        count_12_bar[0] = -1.0
                    elif count_12_entry_touched:
                        if count_12_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_12_side[0] = 0.0
                        count_12_entry[0] = nan
                        count_12_sl[0] = nan
                        count_12_tp[0] = nan
                        count_12_day[0] = nan
                        count_12_bar[0] = -1.0

                if count_13_side[0] != 0.0 and self.bar_index > count_13_bar[0]:
                    count_13_entry_touched = (
                        self.low[0] <= count_13_entry[0]
                        if count_13_side[0] == 1.0 else
                        self.high[0] >= count_13_entry[0]
                    )
                    count_13_sl_touched = (
                        self.low[0] <= count_13_sl[0]
                        if count_13_side[0] == 1.0 else
                        self.high[0] >= count_13_sl[0]
                    )
                    count_13_tp_touched = (
                        self.high[0] >= count_13_tp[0]
                        if count_13_side[0] == 1.0 else
                        self.low[0] <= count_13_tp[0]
                    )
                    if count_13_sl_touched or count_13_tp_touched:
                        if count_13_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_13_side[0] = 0.0
                        count_13_entry[0] = nan
                        count_13_sl[0] = nan
                        count_13_tp[0] = nan
                        count_13_day[0] = nan
                        count_13_bar[0] = -1.0
                    elif count_13_entry_touched:
                        if count_13_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_13_side[0] = 0.0
                        count_13_entry[0] = nan
                        count_13_sl[0] = nan
                        count_13_tp[0] = nan
                        count_13_day[0] = nan
                        count_13_bar[0] = -1.0

                if count_14_side[0] != 0.0 and self.bar_index > count_14_bar[0]:
                    count_14_entry_touched = (
                        self.low[0] <= count_14_entry[0]
                        if count_14_side[0] == 1.0 else
                        self.high[0] >= count_14_entry[0]
                    )
                    count_14_sl_touched = (
                        self.low[0] <= count_14_sl[0]
                        if count_14_side[0] == 1.0 else
                        self.high[0] >= count_14_sl[0]
                    )
                    count_14_tp_touched = (
                        self.high[0] >= count_14_tp[0]
                        if count_14_side[0] == 1.0 else
                        self.low[0] <= count_14_tp[0]
                    )
                    if count_14_sl_touched or count_14_tp_touched:
                        if count_14_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_14_side[0] = 0.0
                        count_14_entry[0] = nan
                        count_14_sl[0] = nan
                        count_14_tp[0] = nan
                        count_14_day[0] = nan
                        count_14_bar[0] = -1.0
                    elif count_14_entry_touched:
                        if count_14_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_14_side[0] = 0.0
                        count_14_entry[0] = nan
                        count_14_sl[0] = nan
                        count_14_tp[0] = nan
                        count_14_day[0] = nan
                        count_14_bar[0] = -1.0

                if count_15_side[0] != 0.0 and self.bar_index > count_15_bar[0]:
                    count_15_entry_touched = (
                        self.low[0] <= count_15_entry[0]
                        if count_15_side[0] == 1.0 else
                        self.high[0] >= count_15_entry[0]
                    )
                    count_15_sl_touched = (
                        self.low[0] <= count_15_sl[0]
                        if count_15_side[0] == 1.0 else
                        self.high[0] >= count_15_sl[0]
                    )
                    count_15_tp_touched = (
                        self.high[0] >= count_15_tp[0]
                        if count_15_side[0] == 1.0 else
                        self.low[0] <= count_15_tp[0]
                    )
                    if count_15_sl_touched or count_15_tp_touched:
                        if count_15_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_15_side[0] = 0.0
                        count_15_entry[0] = nan
                        count_15_sl[0] = nan
                        count_15_tp[0] = nan
                        count_15_day[0] = nan
                        count_15_bar[0] = -1.0
                    elif count_15_entry_touched:
                        if count_15_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_15_side[0] = 0.0
                        count_15_entry[0] = nan
                        count_15_sl[0] = nan
                        count_15_tp[0] = nan
                        count_15_day[0] = nan
                        count_15_bar[0] = -1.0

                if count_16_side[0] != 0.0 and self.bar_index > count_16_bar[0]:
                    count_16_entry_touched = (
                        self.low[0] <= count_16_entry[0]
                        if count_16_side[0] == 1.0 else
                        self.high[0] >= count_16_entry[0]
                    )
                    count_16_sl_touched = (
                        self.low[0] <= count_16_sl[0]
                        if count_16_side[0] == 1.0 else
                        self.high[0] >= count_16_sl[0]
                    )
                    count_16_tp_touched = (
                        self.high[0] >= count_16_tp[0]
                        if count_16_side[0] == 1.0 else
                        self.low[0] <= count_16_tp[0]
                    )
                    if count_16_sl_touched or count_16_tp_touched:
                        if count_16_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_16_side[0] = 0.0
                        count_16_entry[0] = nan
                        count_16_sl[0] = nan
                        count_16_tp[0] = nan
                        count_16_day[0] = nan
                        count_16_bar[0] = -1.0
                    elif count_16_entry_touched:
                        if count_16_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_16_side[0] = 0.0
                        count_16_entry[0] = nan
                        count_16_sl[0] = nan
                        count_16_tp[0] = nan
                        count_16_day[0] = nan
                        count_16_bar[0] = -1.0

                if count_17_side[0] != 0.0 and self.bar_index > count_17_bar[0]:
                    count_17_entry_touched = (
                        self.low[0] <= count_17_entry[0]
                        if count_17_side[0] == 1.0 else
                        self.high[0] >= count_17_entry[0]
                    )
                    count_17_sl_touched = (
                        self.low[0] <= count_17_sl[0]
                        if count_17_side[0] == 1.0 else
                        self.high[0] >= count_17_sl[0]
                    )
                    count_17_tp_touched = (
                        self.high[0] >= count_17_tp[0]
                        if count_17_side[0] == 1.0 else
                        self.low[0] <= count_17_tp[0]
                    )
                    if count_17_sl_touched or count_17_tp_touched:
                        if count_17_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_17_side[0] = 0.0
                        count_17_entry[0] = nan
                        count_17_sl[0] = nan
                        count_17_tp[0] = nan
                        count_17_day[0] = nan
                        count_17_bar[0] = -1.0
                    elif count_17_entry_touched:
                        if count_17_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_17_side[0] = 0.0
                        count_17_entry[0] = nan
                        count_17_sl[0] = nan
                        count_17_tp[0] = nan
                        count_17_day[0] = nan
                        count_17_bar[0] = -1.0

                if count_18_side[0] != 0.0 and self.bar_index > count_18_bar[0]:
                    count_18_entry_touched = (
                        self.low[0] <= count_18_entry[0]
                        if count_18_side[0] == 1.0 else
                        self.high[0] >= count_18_entry[0]
                    )
                    count_18_sl_touched = (
                        self.low[0] <= count_18_sl[0]
                        if count_18_side[0] == 1.0 else
                        self.high[0] >= count_18_sl[0]
                    )
                    count_18_tp_touched = (
                        self.high[0] >= count_18_tp[0]
                        if count_18_side[0] == 1.0 else
                        self.low[0] <= count_18_tp[0]
                    )
                    if count_18_sl_touched or count_18_tp_touched:
                        if count_18_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_18_side[0] = 0.0
                        count_18_entry[0] = nan
                        count_18_sl[0] = nan
                        count_18_tp[0] = nan
                        count_18_day[0] = nan
                        count_18_bar[0] = -1.0
                    elif count_18_entry_touched:
                        if count_18_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_18_side[0] = 0.0
                        count_18_entry[0] = nan
                        count_18_sl[0] = nan
                        count_18_tp[0] = nan
                        count_18_day[0] = nan
                        count_18_bar[0] = -1.0

                if count_19_side[0] != 0.0 and self.bar_index > count_19_bar[0]:
                    count_19_entry_touched = (
                        self.low[0] <= count_19_entry[0]
                        if count_19_side[0] == 1.0 else
                        self.high[0] >= count_19_entry[0]
                    )
                    count_19_sl_touched = (
                        self.low[0] <= count_19_sl[0]
                        if count_19_side[0] == 1.0 else
                        self.high[0] >= count_19_sl[0]
                    )
                    count_19_tp_touched = (
                        self.high[0] >= count_19_tp[0]
                        if count_19_side[0] == 1.0 else
                        self.low[0] <= count_19_tp[0]
                    )
                    if count_19_sl_touched or count_19_tp_touched:
                        if count_19_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_19_side[0] = 0.0
                        count_19_entry[0] = nan
                        count_19_sl[0] = nan
                        count_19_tp[0] = nan
                        count_19_day[0] = nan
                        count_19_bar[0] = -1.0
                    elif count_19_entry_touched:
                        if count_19_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_19_side[0] = 0.0
                        count_19_entry[0] = nan
                        count_19_sl[0] = nan
                        count_19_tp[0] = nan
                        count_19_day[0] = nan
                        count_19_bar[0] = -1.0

                if count_20_side[0] != 0.0 and self.bar_index > count_20_bar[0]:
                    count_20_entry_touched = (
                        self.low[0] <= count_20_entry[0]
                        if count_20_side[0] == 1.0 else
                        self.high[0] >= count_20_entry[0]
                    )
                    count_20_sl_touched = (
                        self.low[0] <= count_20_sl[0]
                        if count_20_side[0] == 1.0 else
                        self.high[0] >= count_20_sl[0]
                    )
                    count_20_tp_touched = (
                        self.high[0] >= count_20_tp[0]
                        if count_20_side[0] == 1.0 else
                        self.low[0] <= count_20_tp[0]
                    )
                    if count_20_sl_touched or count_20_tp_touched:
                        if count_20_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_20_side[0] = 0.0
                        count_20_entry[0] = nan
                        count_20_sl[0] = nan
                        count_20_tp[0] = nan
                        count_20_day[0] = nan
                        count_20_bar[0] = -1.0
                    elif count_20_entry_touched:
                        if count_20_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_20_side[0] = 0.0
                        count_20_entry[0] = nan
                        count_20_sl[0] = nan
                        count_20_tp[0] = nan
                        count_20_day[0] = nan
                        count_20_bar[0] = -1.0

                if not rr_setting_changed:
                    count_sell_ready = sell_condition or sell_breakout_pullback_ready
                    count_buy_ready = buy_condition or buy_breakout_pullback_ready

                    if count_sell_ready and not count_buy_ready:
                        count_new_entry = candidate_entry_price
                        count_recent_high = max([
                            self.high[0], self.high[1], self.high[2], self.high[3],
                            self.high[4], self.high[5], self.high[6], self.high[7]
                        ])
                        count_stop_buffer = max(candle_range * 0.25, abs(count_new_entry) * 0.00005)
                        count_new_stop = max(count_recent_high, count_new_entry + count_stop_buffer)
                        count_new_risk = count_new_stop - count_new_entry
                        count_new_distance = abs(count_new_entry - count_new_stop)
                        count_new_side = -1.0
                    elif count_buy_ready:
                        count_new_entry = candidate_entry_price
                        count_recent_low = min([
                            self.low[0], self.low[1], self.low[2], self.low[3],
                            self.low[4], self.low[5], self.low[6], self.low[7]
                        ])
                        count_stop_buffer = max(candle_range * 0.25, abs(count_new_entry) * 0.00005)
                        count_new_stop = min(count_recent_low, count_new_entry - count_stop_buffer)
                        count_new_risk = count_new_entry - count_new_stop
                        count_new_distance = abs(count_new_entry - count_new_stop)
                        count_new_side = 1.0
                    else:
                        count_new_risk = 0.0
                        count_new_distance = 0.0

                    count_new_risk_per_lot = count_new_distance * self.contract_size
                    count_new_lot = 0.0
                    if count_new_risk_per_lot > 0.0 and risk_budget_cash > 0.0:
                        count_new_lot = int((risk_budget_cash / count_new_risk_per_lot) * 100.0) / 100.0

                    if (
                        count_new_side != 0.0
                        and count_new_risk > 0.0
                        and count_new_distance <= maximum_allowed_sl_distance
                        and count_new_lot >= 0.01
                    ):
                        if count_1_side[0] == 0.0:
                            count_1_side[0] = count_new_side
                            count_1_entry[0] = count_new_entry
                            count_1_sl[0] = count_new_stop
                            count_1_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_1_day[0] = current_ist_day_key
                            count_1_bar[0] = float(self.bar_index)
                        elif count_2_side[0] == 0.0:
                            count_2_side[0] = count_new_side
                            count_2_entry[0] = count_new_entry
                            count_2_sl[0] = count_new_stop
                            count_2_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_2_day[0] = current_ist_day_key
                            count_2_bar[0] = float(self.bar_index)
                        elif count_3_side[0] == 0.0:
                            count_3_side[0] = count_new_side
                            count_3_entry[0] = count_new_entry
                            count_3_sl[0] = count_new_stop
                            count_3_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_3_day[0] = current_ist_day_key
                            count_3_bar[0] = float(self.bar_index)
                        elif count_4_side[0] == 0.0:
                            count_4_side[0] = count_new_side
                            count_4_entry[0] = count_new_entry
                            count_4_sl[0] = count_new_stop
                            count_4_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_4_day[0] = current_ist_day_key
                            count_4_bar[0] = float(self.bar_index)
                        elif count_5_side[0] == 0.0:
                            count_5_side[0] = count_new_side
                            count_5_entry[0] = count_new_entry
                            count_5_sl[0] = count_new_stop
                            count_5_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_5_day[0] = current_ist_day_key
                            count_5_bar[0] = float(self.bar_index)
                        elif count_6_side[0] == 0.0:
                            count_6_side[0] = count_new_side
                            count_6_entry[0] = count_new_entry
                            count_6_sl[0] = count_new_stop
                            count_6_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_6_day[0] = current_ist_day_key
                            count_6_bar[0] = float(self.bar_index)
                        elif count_7_side[0] == 0.0:
                            count_7_side[0] = count_new_side
                            count_7_entry[0] = count_new_entry
                            count_7_sl[0] = count_new_stop
                            count_7_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_7_day[0] = current_ist_day_key
                            count_7_bar[0] = float(self.bar_index)
                        elif count_8_side[0] == 0.0:
                            count_8_side[0] = count_new_side
                            count_8_entry[0] = count_new_entry
                            count_8_sl[0] = count_new_stop
                            count_8_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_8_day[0] = current_ist_day_key
                            count_8_bar[0] = float(self.bar_index)
                        elif count_9_side[0] == 0.0:
                            count_9_side[0] = count_new_side
                            count_9_entry[0] = count_new_entry
                            count_9_sl[0] = count_new_stop
                            count_9_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_9_day[0] = current_ist_day_key
                            count_9_bar[0] = float(self.bar_index)
                        elif count_10_side[0] == 0.0:
                            count_10_side[0] = count_new_side
                            count_10_entry[0] = count_new_entry
                            count_10_sl[0] = count_new_stop
                            count_10_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_10_day[0] = current_ist_day_key
                            count_10_bar[0] = float(self.bar_index)
                        elif count_11_side[0] == 0.0:
                            count_11_side[0] = count_new_side
                            count_11_entry[0] = count_new_entry
                            count_11_sl[0] = count_new_stop
                            count_11_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_11_day[0] = current_ist_day_key
                            count_11_bar[0] = float(self.bar_index)
                        elif count_12_side[0] == 0.0:
                            count_12_side[0] = count_new_side
                            count_12_entry[0] = count_new_entry
                            count_12_sl[0] = count_new_stop
                            count_12_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_12_day[0] = current_ist_day_key
                            count_12_bar[0] = float(self.bar_index)
                        elif count_13_side[0] == 0.0:
                            count_13_side[0] = count_new_side
                            count_13_entry[0] = count_new_entry
                            count_13_sl[0] = count_new_stop
                            count_13_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_13_day[0] = current_ist_day_key
                            count_13_bar[0] = float(self.bar_index)
                        elif count_14_side[0] == 0.0:
                            count_14_side[0] = count_new_side
                            count_14_entry[0] = count_new_entry
                            count_14_sl[0] = count_new_stop
                            count_14_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_14_day[0] = current_ist_day_key
                            count_14_bar[0] = float(self.bar_index)
                        elif count_15_side[0] == 0.0:
                            count_15_side[0] = count_new_side
                            count_15_entry[0] = count_new_entry
                            count_15_sl[0] = count_new_stop
                            count_15_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_15_day[0] = current_ist_day_key
                            count_15_bar[0] = float(self.bar_index)
                        elif count_16_side[0] == 0.0:
                            count_16_side[0] = count_new_side
                            count_16_entry[0] = count_new_entry
                            count_16_sl[0] = count_new_stop
                            count_16_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_16_day[0] = current_ist_day_key
                            count_16_bar[0] = float(self.bar_index)
                        elif count_17_side[0] == 0.0:
                            count_17_side[0] = count_new_side
                            count_17_entry[0] = count_new_entry
                            count_17_sl[0] = count_new_stop
                            count_17_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_17_day[0] = current_ist_day_key
                            count_17_bar[0] = float(self.bar_index)
                        elif count_18_side[0] == 0.0:
                            count_18_side[0] = count_new_side
                            count_18_entry[0] = count_new_entry
                            count_18_sl[0] = count_new_stop
                            count_18_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_18_day[0] = current_ist_day_key
                            count_18_bar[0] = float(self.bar_index)
                        elif count_19_side[0] == 0.0:
                            count_19_side[0] = count_new_side
                            count_19_entry[0] = count_new_entry
                            count_19_sl[0] = count_new_stop
                            count_19_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_19_day[0] = current_ist_day_key
                            count_19_bar[0] = float(self.bar_index)
                        elif count_20_side[0] == 0.0:
                            count_20_side[0] = count_new_side
                            count_20_entry[0] = count_new_entry
                            count_20_sl[0] = count_new_stop
                            count_20_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_20_day[0] = current_ist_day_key
                            count_20_bar[0] = float(self.bar_index)
                        # If all 20 slots are occupied, do not overwrite an unresolved setup.
            # ================================================
            # NEW PRIMARY ENTRY
            # ================================================

            # Never commit an entry, set active trade state, or expose an
            # absolute entry marker while this candle is still forming.
            # Setup conditions may develop intrabar, but the final entry/SL/TP
            # calculation is committed only on the candle-close callback.
            if (
                self.is_closed_bar and side[0] == 0.0
                and pending_trade_side[0] == 0.0 and not trade_exited
            ):

                # Preserve the original signal conditions without a deviation
                # filter. Entry 1 uses the confirmation candle midpoint.
                sell_entry_ready = sell_condition or sell_breakout_pullback_ready
                buy_entry_ready = buy_condition or buy_breakout_pullback_ready

                if sell_entry_ready and not buy_entry_ready:

                    recent_high = max([
                        self.high[0], self.high[1],
                        self.high[2], self.high[3],
                        self.high[4], self.high[5],
                        self.high[6], self.high[7]
                    ])

                    # Preserve the original midpoint setup and sizing exactly.
                    # The midpoint determines the original SL, TP and total lot.
                    entry_price = candidate_entry_price

                    if sell_breakout_pullback_ready:
                        sell_reason = 'BREAKOUT + VOLUME PULLBACK'

                    stop_price = recent_high
                    entry_stop_buffer = max(
                        candle_range * 0.25,
                        abs(entry_price) * 0.00005
                    )
                    stop_price = max(
                        stop_price,
                        entry_price + entry_stop_buffer
                    )

                    risk = stop_price - entry_price
                    sl_distance = abs(entry_price - stop_price)
                    risk_per_one_lot = sl_distance * self.contract_size
                    calculated_lot = 0.0
                    calculated_risk_cash = nan

                    if risk_per_one_lot > 0.0 and risk_budget_cash > 0.0:
                        raw_lot = risk_budget_cash / risk_per_one_lot
                        calculated_lot = int(raw_lot * 100.0) / 100.0
                        calculated_risk_cash = (
                            calculated_lot * risk_per_one_lot
                        )

                    # Allocate half of the dollar risk budget to the midpoint leg.
                    # The remaining budget is reserved for the immediate leg after midpoint fill.
                    midpoint_risk_per_lot = sl_distance * self.contract_size
                    mid_lot = 0.0
                    if midpoint_risk_per_lot > 0.0 and risk_budget_cash > 0.0:
                        midpoint_half_budget = risk_budget_cash * 0.50
                        mid_lot = int((midpoint_half_budget / midpoint_risk_per_lot) * 100.0) / 100.0

                    mid_risk_cash_value = mid_lot * midpoint_risk_per_lot

                    if (
                        risk > 0.0
                        and sl_distance <= maximum_allowed_sl_distance
                        and mid_lot >= 0.01
                        and mid_risk_cash_value <= risk_budget_cash
                    ):
                        target_price = entry_price - risk * rr_multiplier

                        # Arm only a pending midpoint order. No active side,
                        # trade P/L, or immediate entry is recorded yet.
                        pending_trade_side[0] = -1.0
                        pending_trade_entry[0] = entry_price
                        pending_mid_entry[0] = entry_price
                        pending_trade_sl[0] = stop_price
                        pending_trade_tp[0] = target_price
                        pending_trade_lot[0] = mid_lot
                        pending_trade_risk_cash[0] = mid_risk_cash_value
                        pending_trade_setup_day[0] = current_ist_day_key
                        pending_trade_setup_bar[0] = float(self.bar_index)

                        entry[0] = nan
                        midpoint_master_entry[0] = entry_price
                        early_leg_entry[0] = entry_price
                        early_leg_lot[0] = 0.0
                        mid_leg_lot[0] = mid_lot
                        mid_leg_active[0] = 0.0
                        early_leg_closed[0] = 0.0
                        early_leg_pnl[0] = 0.0
                        mid_leg_pnl[0] = 0.0
                        setup_risk_budget[0] = risk_budget_cash
                        sl[0] = stop_price
                        tp[0] = target_price
                        side[0] = 0.0
                        trade_lot[0] = nan
                        trade_risk_cash[0] = nan
                        original_risk_distance[0] = sl_distance
                        favorable_extreme[0] = entry_price
                        trail_candidate[0] = nan
                        trail_confirm_count[0] = 0.0
                        trail_stage[0] = 0.0
                        trail_last_update_bar[0] = -1.0
                        early_exit_warned[0] = 0.0
                        entry_count[0] = 0.0
                        last_entry_bar[0] = -1.0
                        last_entry_price[0] = nan
                        entry_label_time[0] = self.time[0]
                        pending_early_entry[0] = nan
                        sell_signal = True

                        pending_buy[0] = 0.0
                        pending_buy_average[0] = nan
                        pending_buy_low[0] = nan
                        pending_buy_bar[0] = -1.0
                        pending_sell[0] = 0.0
                        pending_sell_average[0] = nan
                        pending_sell_high[0] = nan
                        pending_sell_bar[0] = -1.0

                elif buy_entry_ready:

                    recent_low = min([
                        self.low[0], self.low[1],
                        self.low[2], self.low[3],
                        self.low[4], self.low[5],
                        self.low[6], self.low[7]
                    ])

                    # Preserve the original midpoint setup and sizing exactly.
                    # The midpoint determines the original SL, TP and total lot.
                    entry_price = candidate_entry_price

                    if buy_breakout_pullback_ready:
                        buy_reason = 'BREAKOUT + VOLUME PULLBACK'

                    stop_price = recent_low
                    entry_stop_buffer = max(
                        candle_range * 0.25,
                        abs(entry_price) * 0.00005
                    )
                    stop_price = min(
                        stop_price,
                        entry_price - entry_stop_buffer
                    )

                    risk = entry_price - stop_price
                    sl_distance = abs(entry_price - stop_price)
                    risk_per_one_lot = sl_distance * self.contract_size
                    calculated_lot = 0.0
                    calculated_risk_cash = nan

                    if risk_per_one_lot > 0.0 and risk_budget_cash > 0.0:
                        raw_lot = risk_budget_cash / risk_per_one_lot
                        calculated_lot = int(raw_lot * 100.0) / 100.0
                        calculated_risk_cash = (
                            calculated_lot * risk_per_one_lot
                        )

                    # Allocate half of the dollar risk budget to the midpoint leg.
                    # The remaining budget is reserved for the immediate leg after midpoint fill.
                    midpoint_risk_per_lot = sl_distance * self.contract_size
                    mid_lot = 0.0
                    if midpoint_risk_per_lot > 0.0 and risk_budget_cash > 0.0:
                        midpoint_half_budget = risk_budget_cash * 0.50
                        mid_lot = int((midpoint_half_budget / midpoint_risk_per_lot) * 100.0) / 100.0

                    mid_risk_cash_value = mid_lot * midpoint_risk_per_lot

                    if (
                        risk > 0.0
                        and sl_distance <= maximum_allowed_sl_distance
                        and mid_lot >= 0.01
                        and mid_risk_cash_value <= risk_budget_cash
                    ):
                        target_price = entry_price + risk * rr_multiplier

                        # Arm only a pending midpoint order. No active side,
                        # trade P/L, or immediate entry is recorded yet.
                        pending_trade_side[0] = 1.0
                        pending_trade_entry[0] = entry_price
                        pending_mid_entry[0] = entry_price
                        pending_trade_sl[0] = stop_price
                        pending_trade_tp[0] = target_price
                        pending_trade_lot[0] = mid_lot
                        pending_trade_risk_cash[0] = mid_risk_cash_value
                        pending_trade_setup_day[0] = current_ist_day_key
                        pending_trade_setup_bar[0] = float(self.bar_index)

                        entry[0] = nan
                        midpoint_master_entry[0] = entry_price
                        early_leg_entry[0] = entry_price
                        early_leg_lot[0] = 0.0
                        mid_leg_lot[0] = mid_lot
                        mid_leg_active[0] = 0.0
                        early_leg_closed[0] = 0.0
                        early_leg_pnl[0] = 0.0
                        mid_leg_pnl[0] = 0.0
                        setup_risk_budget[0] = risk_budget_cash
                        sl[0] = stop_price
                        tp[0] = target_price
                        side[0] = 0.0
                        trade_lot[0] = nan
                        trade_risk_cash[0] = nan
                        original_risk_distance[0] = sl_distance
                        favorable_extreme[0] = entry_price
                        trail_candidate[0] = nan
                        trail_confirm_count[0] = 0.0
                        trail_stage[0] = 0.0
                        trail_last_update_bar[0] = -1.0
                        early_exit_warned[0] = 0.0
                        entry_count[0] = 0.0
                        last_entry_bar[0] = -1.0
                        last_entry_price[0] = nan
                        entry_label_time[0] = self.time[0]
                        pending_early_entry[0] = nan
                        buy_signal = True

                        pending_buy[0] = 0.0
                        pending_buy_average[0] = nan
                        pending_buy_low[0] = nan
                        pending_buy_bar[0] = -1.0
                        pending_sell[0] = 0.0
                        pending_sell_average[0] = nan
                        pending_sell_high[0] = nan
                        pending_sell_bar[0] = -1.0

                        if not (
                            self.delete_setup == 'Primary BUY'
                            and self.bar_index == self.delete_bar_index
                        ):

                            if self.is_closed_bar:

                                pass

        # ====================================================
        # ONE COMBINED TRADE DESCRIPTION BOX
        # ====================================================

        new_trade_entry_event = (
            last_entry_bar[0] == self.bar_index
        )

        # ====================================================
        # LOT LABEL ONLY AT TRADE ENTRY
        # PROFIT / LOSS LABELS ARE DRAWN ONLY AFTER EXIT
        # ====================================================

        if (
            self.show_entry_descriptions
            and new_trade_entry_event
            and side[0] != 0.0
        ):

            is_buy = side[0] == 1.0

            trade_symbol = ''

            entry1_description_reason = (
                buy_reason if is_buy else sell_reason
            )

            entry2_description_reason = ''
            addon_zone_reason = ''

            if is_buy:

                if bullish_breakout_volume_setup or buy_reason == 'BREAKOUT + VOLUME PULLBACK':
                    entry2_description_reason = 'Breakout Pullback'

                elif bullish_engulfing:
                    entry2_description_reason = 'Engulf'

                elif bullish_hammer:
                    entry2_description_reason = 'Hammer'

                elif morning_star:
                    entry2_description_reason = 'MStar'

                elif bullish_rejection:
                    entry2_description_reason = 'Reject'

                elif bullish_break_previous:
                    entry2_description_reason = 'BrkHi'

                elif bullish_strong_body:
                    entry2_description_reason = 'Strong'

                else:
                    entry2_description_reason = 'PA'

                if support_zone:
                    entry2_description_reason += ' + Support'
                    addon_zone_reason += ' + Support'

                if bullish_ob_touch:
                    entry2_description_reason += ' + OB'
                    addon_zone_reason += ' + OB'

                if bullish_fvg_touch:
                    entry2_description_reason += ' + FVG'
                    addon_zone_reason += ' + FVG'

                if self.close[0] > ema9[0] and self.close[0] > ema20[0]:
                    entry2_description_reason += ' + EMA'

                if rsi[0] > rsi[1] and rsi[0] > 40:
                    entry2_description_reason += ' + RSI'

            else:

                if bearish_breakout_volume_setup or sell_reason == 'BREAKOUT + VOLUME PULLBACK':
                    entry2_description_reason = 'Breakout Pullback'

                elif bearish_engulfing or bearish_close_momentum:
                    entry2_description_reason = 'Engulf'

                elif bearish_shooting_star:
                    entry2_description_reason = 'SStar'

                elif evening_star:
                    entry2_description_reason = 'Evening Star'

                elif bearish_rejection:
                    entry2_description_reason = 'Reject'

                elif bearish_break_previous:
                    entry2_description_reason = 'BrkLo'

                elif bearish_strong_body:
                    entry2_description_reason = 'Strong'

                else:
                    entry2_description_reason = 'PA'

                if resistance_zone:
                    entry2_description_reason += ' + Resistance'
                    addon_zone_reason += ' + Resistance'

                if bearish_ob_touch:
                    entry2_description_reason += ' + OB'
                    addon_zone_reason += ' + OB'

                if bearish_fvg_touch:
                    entry2_description_reason += ' + FVG'
                    addon_zone_reason += ' + FVG'

                if self.close[0] < ema9[0] and self.close[0] < ema20[0]:
                    entry2_description_reason += ' + EMA'

                if rsi[0] < rsi[1] and rsi[0] < 60:
                    entry2_description_reason += ' + RSI'

            entry345_description_reason = 'PA' + addon_zone_reason

            sl_text = ' | SL ' + str(round(sl[0], 2))
            tp_text = ' | TP ' + str(round(tp[0], 2))
            lot_text = ''

            if trade_lot[0] == trade_lot[0]:
                lot_text = (
                    ' | TOTAL LOT ' + str(round(trade_lot[0], 2))
                    + ' | RISK $'
                    + str(round(trade_risk_cash[0], 2))
                )

            combined_trade_description = ''

            if entry[0] == entry[0]:

                combined_trade_description += (
                    trade_symbol + ' 1 @ ' + str(round(entry[0], 2))
                    + sl_text + tp_text + lot_text
                    + ' | Reason: ' + entry1_description_reason
                )

            if second_entry_price[0] == second_entry_price[0]:

                if combined_trade_description != '':
                    combined_trade_description += '\n'

                combined_trade_description += (
                    trade_symbol + ' 2 @ '
                    + str(round(second_entry_price[0], 2))
                    + sl_text + tp_text
                    + ' | Reason: ' + entry2_description_reason
                )

            if third_entry_price[0] == third_entry_price[0]:

                if combined_trade_description != '':
                    combined_trade_description += '\n'

                combined_trade_description += (
                    trade_symbol + ' 3 @ '
                    + str(round(third_entry_price[0], 2))
                    + sl_text + tp_text
                    + ' | Reason: ' + entry345_description_reason
                )

            if fourth_entry_price[0] == fourth_entry_price[0]:

                if combined_trade_description != '':
                    combined_trade_description += '\n'

                combined_trade_description += (
                    trade_symbol + ' 4 @ '
                    + str(round(fourth_entry_price[0], 2))
                    + sl_text + tp_text
                    + ' | Reason: ' + entry345_description_reason
                )

            if fifth_entry_price[0] == fifth_entry_price[0]:

                if combined_trade_description != '':
                    combined_trade_description += '\n'

                combined_trade_description += (
                    trade_symbol + ' 5 @ '
                    + str(round(fifth_entry_price[0], 2))
                    + sl_text + tp_text
                    + ' | Reason: ' + entry345_description_reason
                )

            if self.is_closed_bar:

                pass

        # ====================================================
        # CURRENT CHART TIMEFRAME DAILY REPORT
        # CLOSED TRADES ONLY - SPREADSHEET STYLE
        # ====================================================

        if self.show_daily_report and self.is_last_bar:

            chart_minutes = self.time_frame.to_minutes()

            timeframe_label = ''

            if chart_minutes < 60:
                timeframe_label = str(chart_minutes) + ' min'
            elif chart_minutes == 60:
                timeframe_label = '1 hour'
            elif chart_minutes % 60 == 0 and chart_minutes < 1440:
                timeframe_label = str(int(chart_minutes / 60)) + ' hours'
            elif chart_minutes >= 1440 and chart_minutes % 1440 == 0:
                timeframe_label = str(int(chart_minutes / 1440)) + ' day'
            else:
                timeframe_label = str(chart_minutes) + ' min'

            sl_count = int(report_sl[0])
            tp_count = int(report_tp[0])
            trailing_sl_count = int(report_trailing_sl[0])
            active_trades = int(report_active_trades[0])
            inactive_trades = int(report_inactive_trades[0])
            total_trades = active_trades + inactive_trades
            total_exits = sl_count + tp_count + trailing_sl_count

            win_rate = 0.0
            if total_exits > 0:
                win_rate = (tp_count / total_exits) * 100.0

            report_year = int(self.report_date / 10000)
            report_month = int((self.report_date % 10000) / 100)
            report_day = int(self.report_date % 100)

            report_day_text = str(report_day)
            report_month_text = str(report_month)

            if report_day < 10:
                report_day_text = '0' + report_day_text

            if report_month < 10:
                report_month_text = '0' + report_month_text

            date_label = (
                report_day_text + '-'
                + report_month_text + '-'
                + str(report_year)
            )

            label_width = 44
            value_width = 18

            top_border = (
                '+' + ('-' * (label_width + 2))
                + '+' + ('-' * (value_width + 2)) + '+'
            )

            header_row = (
                '| ' + '𝗞𝗦 𝗧𝗥𝗔𝗗𝗘𝗥 𝗗𝗘𝗦𝗞 - 𝗗𝗔𝗜𝗟𝗬 / 𝗠𝗢𝗡𝗧𝗛𝗟𝗬 𝗣/𝗟'.ljust(label_width) + ' | '
                + 'RESULT'.ljust(value_width) + ' |'
            )

            date_row = (
                '| ' + 'Date'.ljust(label_width) + ' | '
                + date_label.ljust(value_width) + ' |'
            )

            timeframe_row = (
                '| ' + 'Time frame'.ljust(label_width) + ' | '
                + timeframe_label.ljust(value_width) + ' |'
            )

            active_row = (
                '| ' + 'Active Trades'.ljust(label_width) + ' | '
                + str(active_trades).ljust(value_width) + ' |'
            )
            inactive_row = (
                '| ' + 'Inactive Trades'.ljust(label_width) + ' | '
                + str(inactive_trades).ljust(value_width) + ' |'
            )
            total_row = (
                '| ' + 'Total trades'.ljust(label_width) + ' | '
                + str(total_trades).ljust(value_width) + ' |'
            )

            active_pnl_row = (
                '| ' + 'Active Trade P/L'.ljust(label_width) + ' | '
                + ('$' + str(round(report_active_pnl[0], 2))).ljust(value_width) + ' |'
            )
            inactive_pnl_row = (
                '| ' + 'Inactive Trade P/L'.ljust(label_width) + ' | '
                + ('$' + str(round(report_inactive_pnl[0], 2))).ljust(value_width) + ' |'
            )

            sl_row = (
                '| ' + 'StopLoss'.ljust(label_width) + ' | '
                + str(sl_count).ljust(value_width) + ' |'
            )

            tp_row = (
                '| ' + 'Target Hit'.ljust(label_width) + ' | '
                + str(tp_count).ljust(value_width) + ' |'
            )

            trailing_sl_text = (
                str(trailing_sl_count) if trailing_sl_count > 0
                else 'No trades hit'
            )
            trailing_sl_row = (
                '| ' + 'Trailing SL Hit'.ljust(label_width) + ' | '
                + trailing_sl_text.ljust(value_width) + ' |'
            )
            win_row = (
                '| ' + 'Win Rate'.ljust(label_width) + ' | '
                + (str(int(round(win_rate))) + '%').ljust(value_width) + ' |'
            )

            rr_row = (
                '| ' + 'Risk Reward'.ljust(label_width) + ' | '
                + self.risk_reward.ljust(value_width) + ' |'
            )

            risk_mode_text = 'REDUCED 3% + 1%' if reduced_risk_mode[0] == 1.0 else 'NORMAL 5% + 2%'
            risk_mode_row = (
                '| ' + 'Current Risk Mode'.ljust(label_width) + ' | '
                + risk_mode_text.ljust(value_width) + ' |'
            )

            net_profit_row = (
                '| ' + 'Daily Net P/L'.ljust(label_width) + ' | '
                + ('$' + str(round(report_net_profit[0], 2))).ljust(value_width) + ' |'
            )

            monthly_net_profit_row = (
                '| ' + 'Monthly Net P/L'.ljust(label_width) + ' | '
                + ('$' + str(round(monthly_net_profit[0], 2))).ljust(value_width) + ' |'
            )

            report_text = (
                top_border + '\n'
                + header_row + '\n'
                + top_border + '\n'
                + date_row + '\n'
                + timeframe_row + '\n'
                + active_row + '\n'
                + inactive_row + '\n'
                + total_row + '\n'
                + active_pnl_row + '\n'
                + inactive_pnl_row + '\n'
                + sl_row + '\n'
                + tp_row + '\n'
                + trailing_sl_row + '\n'
                + win_row + '\n'
                + rr_row + '\n'
                + risk_mode_row + '\n'
                + net_profit_row + '\n'
                + monthly_net_profit_row
            )

            # Optional daily breakdown for the selected month, through the current IST date.
            if self.show_monthly_daily_breakdown:
                report_text += '\n' + top_border
                report_text += '\n| ' + 'MONTHLY DAILY NET P/L'.ljust(label_width) + ' | ' + 'AMOUNT'.ljust(value_width) + ' |'
                report_text += '\n' + top_border

                days_in_selected_month = int(
                    self._selected_report_month_end_key
                    - self._selected_report_month_start_key
                )
                current_month_day_limit = int(
                    max(
                        0.0,
                        min(
                            float(days_in_selected_month),
                            current_ist_day_key - self._selected_report_month_start_key + 1.0
                        )
                    )
                )

                month_names = [
                    '', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
                ]
                selected_month_name = month_names[report_month]

                for day_number in range(1, current_month_day_limit + 1):
                    day_profit = 0.0

                    if day_number == 1:
                        day_profit = monthly_day_01_profit[0]
                    elif day_number == 2:
                        day_profit = monthly_day_02_profit[0]
                    elif day_number == 3:
                        day_profit = monthly_day_03_profit[0]
                    elif day_number == 4:
                        day_profit = monthly_day_04_profit[0]
                    elif day_number == 5:
                        day_profit = monthly_day_05_profit[0]
                    elif day_number == 6:
                        day_profit = monthly_day_06_profit[0]
                    elif day_number == 7:
                        day_profit = monthly_day_07_profit[0]
                    elif day_number == 8:
                        day_profit = monthly_day_08_profit[0]
                    elif day_number == 9:
                        day_profit = monthly_day_09_profit[0]
                    elif day_number == 10:
                        day_profit = monthly_day_10_profit[0]
                    elif day_number == 11:
                        day_profit = monthly_day_11_profit[0]
                    elif day_number == 12:
                        day_profit = monthly_day_12_profit[0]
                    elif day_number == 13:
                        day_profit = monthly_day_13_profit[0]
                    elif day_number == 14:
                        day_profit = monthly_day_14_profit[0]
                    elif day_number == 15:
                        day_profit = monthly_day_15_profit[0]
                    elif day_number == 16:
                        day_profit = monthly_day_16_profit[0]
                    elif day_number == 17:
                        day_profit = monthly_day_17_profit[0]
                    elif day_number == 18:
                        day_profit = monthly_day_18_profit[0]
                    elif day_number == 19:
                        day_profit = monthly_day_19_profit[0]
                    elif day_number == 20:
                        day_profit = monthly_day_20_profit[0]
                    elif day_number == 21:
                        day_profit = monthly_day_21_profit[0]
                    elif day_number == 22:
                        day_profit = monthly_day_22_profit[0]
                    elif day_number == 23:
                        day_profit = monthly_day_23_profit[0]
                    elif day_number == 24:
                        day_profit = monthly_day_24_profit[0]
                    elif day_number == 25:
                        day_profit = monthly_day_25_profit[0]
                    elif day_number == 26:
                        day_profit = monthly_day_26_profit[0]
                    elif day_number == 27:
                        day_profit = monthly_day_27_profit[0]
                    elif day_number == 28:
                        day_profit = monthly_day_28_profit[0]
                    elif day_number == 29:
                        day_profit = monthly_day_29_profit[0]
                    elif day_number == 30:
                        day_profit = monthly_day_30_profit[0]
                    elif day_number == 31:
                        day_profit = monthly_day_31_profit[0]

                    daily_date_text = selected_month_name + ' ' + str(day_number)
                    daily_amount_text = '$' + str(round(day_profit, 2))
                    report_text += (
                        '\n| ' + daily_date_text.ljust(label_width)
                        + ' | ' + daily_amount_text.ljust(value_width) + ' |'
                    )

                report_text += '\n' + top_border
            else:
                report_text += '\n' + top_border

            self._daily_report_label.text = report_text
            self.chart.draw(self._daily_report_label)

        # Bar number is intentionally omitted from chart drawings.

        # ====================================================
        # PRIMARY ENTRY MARKER - RESTORED FROM ORIGINAL REPO
        # ====================================================

        marker_price = nan

        if (
            buy_signal
            and not (
                self.delete_setup == 'Primary BUY'
                and self.bar_index == self.delete_bar_index
            )
        ):
            marker_price = self.low[0] - entry_marker_offset

        elif (
            sell_signal
            and not (
                self.delete_setup == 'Primary SELL'
                and self.bar_index == self.delete_bar_index
            )
        ):
            marker_price = self.high[0] + entry_marker_offset

        marker_color = (
            color.RED
            if buy_signal or sell_signal
            else color.TRANSPARENT
        )

        # ====================================================
        # VISUAL TRADE LEVELS
        # Keep the planned Entry / SL / TP visible from the setup
        # candle while the order is pending. This is display-only;
        # internal active-trade calculations continue using entry/sl/tp.
        # ====================================================

        plot_entry_value = entry[0]
        plot_sl_value = sl[0]
        plot_tp_value = tp[0]

        if side[0] != 0.0:
            plot_entry_value = midpoint_master_entry[0]
            plot_sl_value = sl[0]
            plot_tp_value = tp[0]

        # ====================================================
        # OUTPUT
        # ====================================================

        return (
            ema9[0],
            ema20[0],
            ema50[0],
            ema200[0],

            plot_entry_value,
            second_entry_price[0],
            third_entry_price[0],
            fourth_entry_price[0],
            fifth_entry_price[0],

            plot_sl_value,
            plot_tp_value,

            plot.Fill(),
            plot.Fill(),

            plot.Marker(
                value=marker_price,
                color=marker_color
            )
        )
 if report_hit_trailing_sl else 'SL -

                    if current_ist_day_key == risk_day_key[0]:
                        daily_realized_pnl[0] = daily_realized_pnl[0] + realized_pnl
                        daily_loss_threshold = daily_start_balance[0] * 0.30
                        if daily_realized_pnl[0] <= -daily_loss_threshold:
                            reduced_risk_mode[0] = 1.0
                        elif daily_realized_pnl[0] >= 0.0:
                            reduced_risk_mode[0] = 0.0

                    if current_ist_day_key == self._selected_report_day_key:
                        if report_hit_trailing_sl:
                            report_trailing_sl[0] = report_trailing_sl[0] + 1.0
                        elif report_hit_sl:
                            report_sl[0] = report_sl[0] + 1.0
                        elif report_hit_tp:
                            report_tp[0] = report_tp[0] + 1.0
                        report_net_profit[0] = report_net_profit[0] + realized_pnl
                        report_active_pnl[0] = report_active_pnl[0] + realized_pnl

                    if (
                        current_ist_day_key >= self._selected_report_month_start_key
                        and current_ist_day_key < self._selected_report_month_end_key
                    ):
                        monthly_net_profit[0] = monthly_net_profit[0] + realized_pnl
                    if current_ist_day_key == self._selected_report_month_start_key + 0.0:
                        monthly_day_01_profit[0] = monthly_day_01_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 1.0:
                        monthly_day_02_profit[0] = monthly_day_02_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 2.0:
                        monthly_day_03_profit[0] = monthly_day_03_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 3.0:
                        monthly_day_04_profit[0] = monthly_day_04_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 4.0:
                        monthly_day_05_profit[0] = monthly_day_05_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 5.0:
                        monthly_day_06_profit[0] = monthly_day_06_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 6.0:
                        monthly_day_07_profit[0] = monthly_day_07_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 7.0:
                        monthly_day_08_profit[0] = monthly_day_08_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 8.0:
                        monthly_day_09_profit[0] = monthly_day_09_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 9.0:
                        monthly_day_10_profit[0] = monthly_day_10_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 10.0:
                        monthly_day_11_profit[0] = monthly_day_11_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 11.0:
                        monthly_day_12_profit[0] = monthly_day_12_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 12.0:
                        monthly_day_13_profit[0] = monthly_day_13_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 13.0:
                        monthly_day_14_profit[0] = monthly_day_14_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 14.0:
                        monthly_day_15_profit[0] = monthly_day_15_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 15.0:
                        monthly_day_16_profit[0] = monthly_day_16_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 16.0:
                        monthly_day_17_profit[0] = monthly_day_17_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 17.0:
                        monthly_day_18_profit[0] = monthly_day_18_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 18.0:
                        monthly_day_19_profit[0] = monthly_day_19_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 19.0:
                        monthly_day_20_profit[0] = monthly_day_20_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 20.0:
                        monthly_day_21_profit[0] = monthly_day_21_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 21.0:
                        monthly_day_22_profit[0] = monthly_day_22_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 22.0:
                        monthly_day_23_profit[0] = monthly_day_23_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 23.0:
                        monthly_day_24_profit[0] = monthly_day_24_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 24.0:
                        monthly_day_25_profit[0] = monthly_day_25_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 25.0:
                        monthly_day_26_profit[0] = monthly_day_26_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 26.0:
                        monthly_day_27_profit[0] = monthly_day_27_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 27.0:
                        monthly_day_28_profit[0] = monthly_day_28_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 28.0:
                        monthly_day_29_profit[0] = monthly_day_29_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 29.0:
                        monthly_day_30_profit[0] = monthly_day_30_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 30.0:
                        monthly_day_31_profit[0] = monthly_day_31_profit[0] + realized_pnl

                entry[0] = nan
                early_leg_entry[0] = nan
                midpoint_master_entry[0] = nan
                early_leg_lot[0] = nan
                mid_leg_lot[0] = nan
                mid_leg_active[0] = 0.0
                early_leg_closed[0] = 0.0
                pending_mid_entry[0] = nan
                pending_early_entry[0] = nan
                pending_trade_side[0] = 0.0
                pending_trade_entry[0] = nan
                pending_trade_sl[0] = nan
                pending_trade_tp[0] = nan
                pending_trade_lot[0] = nan
                pending_trade_risk_cash[0] = nan
                pending_trade_setup_day[0] = nan
                pending_trade_setup_bar[0] = -1.0
                second_entry_price[0] = nan
                third_entry_price[0] = nan
                fourth_entry_price[0] = nan
                fifth_entry_price[0] = nan
                sl[0] = nan
                tp[0] = nan
                side[0] = 0.0
                trade_lot[0] = nan
                trade_risk_cash[0] = nan
                original_risk_distance[0] = nan
                favorable_extreme[0] = nan
                trail_candidate[0] = nan
                trail_confirm_count[0] = 0.0
                trail_stage[0] = 0.0
                trail_last_update_bar[0] = -1.0
                entry_count[0] = 0.0
                last_entry_bar[0] = -1.0
                last_entry_price[0] = nan
                entry_label_time[0] = nan
                early_exit_warned[0] = 0.0
                pending_buy[0] = 0.0
                pending_buy_average[0] = nan
                pending_buy_low[0] = nan
                pending_buy_bar[0] = -1.0
                pending_sell[0] = 0.0
                pending_sell_average[0] = nan
                pending_sell_high[0] = nan
                pending_sell_bar[0] = -1.0
                trade_exited = True

            # ================================================
            # ADAPTIVE HYBRID TRAILING (M1, CLOSED CANDLES ONLY)
            # ================================================
            # This is a chart-side simulated stop line. Exness Indie custom
            # indicators cannot modify an actual broker position's SL.
            if (
                self.adaptive_trailing_enabled
                and self._is_m1_chart
                and side[0] != 0.0
                and mid_leg_active[0] == 1.0
                and self.bar_index > last_entry_bar[0]
                and original_risk_distance[0] > 0.0
                and not trade_exited
            ):
                is_buy_trail = side[0] == 1.0
                entry[0] = midpoint_master_entry[0]
                risk_unit = original_risk_distance[0]
                atr_value = atr14[0]
                adx_value = adx14[0]
                minus_value = minus_di[0]
                plus_value = plus_di[0]
                proposed_sl = sl[0]

                # Track the best favourable excursion since the simulated entry.
                # Declare shared-scope values before the BUY/SELL branches.
                favourable_move = 0.0
                target_distance = 0.0
                if is_buy_trail:
                    if isnan(favorable_extreme[0]):
                        favorable_extreme[0] = self.high[0]
                    else:
                        favorable_extreme[0] = max(favorable_extreme[0], self.high[0])
                    favourable_move = favorable_extreme[0] - entry[0]
                    target_distance = tp[0] - entry[0]
                else:
                    if isnan(favorable_extreme[0]):
                        favorable_extreme[0] = self.low[0]
                    else:
                        favorable_extreme[0] = min(favorable_extreme[0], self.low[0])
                    favourable_move = entry[0] - favorable_extreme[0]
                    target_distance = entry[0] - tp[0]

                r_progress = favourable_move / risk_unit if risk_unit > 0.0 else 0.0
                tp_progress = (
                    favourable_move / target_distance
                    if target_distance > 0.0 else 0.0
                )

                # 1R: break-even (optional user-supplied cost buffer).
                if r_progress >= 1.0:
                    if is_buy_trail:
                        proposed_sl = max(proposed_sl, entry[0] + self.break_even_buffer)
                    else:
                        proposed_sl = min(proposed_sl, entry[0] - self.break_even_buffer)

                # TP progress locks are based on the ORIGINAL risk distance.
                if tp_progress >= 0.95:
                    lock_price = 0.60 * risk_unit
                    if is_buy_trail:
                        proposed_sl = max(proposed_sl, entry[0] + lock_price)
                    else:
                        proposed_sl = min(proposed_sl, entry[0] - lock_price)
                elif tp_progress >= 0.85:
                    lock_price = 0.30 * risk_unit
                    if is_buy_trail:
                        proposed_sl = max(proposed_sl, entry[0] + lock_price)
                    else:
                        proposed_sl = min(proposed_sl, entry[0] - lock_price)

                # Swing structure + ATR trailing begins after 1.4R.
                if r_progress >= 1.4 and not isnan(atr_value) and atr_value > 0.0:
                    strong_buy_trend = (
                        adx_value >= 25.0
                        and plus_value > minus_value
                        and trail_ema9[0] > trail_ema21[0]
                    )
                    strong_sell_trend = (
                        adx_value >= 25.0
                        and minus_value > plus_value
                        and trail_ema9[0] < trail_ema21[0]
                    )
                    atr_multiplier = 1.5 if (
                        (is_buy_trail and strong_buy_trend)
                        or ((not is_buy_trail) and strong_sell_trend)
                    ) else 1.0
                    atr_buffer = atr_value * atr_multiplier

                    if is_buy_trail:
                        # Confirmed pivot low: two bars on either side.
                        confirmed_swing_low = (
                            self.low[2] < self.low[1]
                            and self.low[2] < self.low[0]
                            and self.low[2] <= self.low[3]
                            and self.low[2] <= self.low[4]
                        )
                        if confirmed_swing_low:
                            swing_candidate = self.low[2] - atr_buffer
                            if swing_candidate > proposed_sl and swing_candidate < self.close[0]:
                                proposed_sl = max(proposed_sl, swing_candidate)

                        # Three bearish closes are a confirmed adverse reaction.
                        bearish_three = (
                            self.close[0] < self.close[1]
                            and self.close[1] < self.close[2]
                            and self.close[0] < trail_ema9[0]
                        )
                        if bearish_three:
                            reaction_candidate = min([
                                self.low[0], self.low[1], self.low[2]
                            ]) - atr_value
                            if reaction_candidate > proposed_sl and reaction_candidate < self.close[0]:
                                proposed_sl = max(proposed_sl, reaction_candidate)
                    else:
                        # Confirmed pivot high: two bars on either side.
                        confirmed_swing_high = (
                            self.high[2] > self.high[1]
                            and self.high[2] > self.high[0]
                            and self.high[2] >= self.high[3]
                            and self.high[2] >= self.high[4]
                        )
                        if confirmed_swing_high:
                            swing_candidate = self.high[2] + atr_buffer
                            if swing_candidate < proposed_sl and swing_candidate > self.close[0]:
                                proposed_sl = min(proposed_sl, swing_candidate)

                        # Three bullish closes are a confirmed adverse reaction.
                        bullish_three = (
                            self.close[0] > self.close[1]
                            and self.close[1] > self.close[2]
                            and self.close[0] > trail_ema9[0]
                        )
                        if bullish_three:
                            reaction_candidate = max([
                                self.high[0], self.high[1], self.high[2]
                            ]) + atr_value
                            if reaction_candidate < proposed_sl and reaction_candidate > self.close[0]:
                                proposed_sl = min(proposed_sl, reaction_candidate)

                # Candidate must improve protection and remain beyond the close.
                candidate_is_valid = (
                    proposed_sl > sl[0] and proposed_sl < self.close[0]
                    if is_buy_trail else
                    proposed_sl < sl[0] and proposed_sl > self.close[0]
                )

                # Require 3 consecutive completed M1 closes to confirm the same
                # or a more protective candidate. Never loosen an existing stop.
                if candidate_is_valid:
                    if is_buy_trail:
                        if isnan(trail_candidate[0]) or proposed_sl > trail_candidate[0]:
                            trail_candidate[0] = proposed_sl
                            trail_confirm_count[0] = 0.0
                    else:
                        if isnan(trail_candidate[0]) or proposed_sl < trail_candidate[0]:
                            trail_candidate[0] = proposed_sl
                            trail_confirm_count[0] = 0.0

                if not isnan(trail_candidate[0]):
                    candidate_still_safe = (
                        self.close[0] > trail_candidate[0]
                        if is_buy_trail else
                        self.close[0] < trail_candidate[0]
                    )
                    if candidate_still_safe:
                        trail_confirm_count[0] = trail_confirm_count[0] + 1.0
                    else:
                        trail_candidate[0] = nan
                        trail_confirm_count[0] = 0.0

                if (
                    not isnan(trail_candidate[0])
                    and trail_confirm_count[0] >= 3.0
                    and (
                        (is_buy_trail and trail_candidate[0] > sl[0])
                        or ((not is_buy_trail) and trail_candidate[0] < sl[0])
                    )
                ):
                    sl[0] = trail_candidate[0]
                    trail_last_update_bar[0] = float(self.bar_index)
                    trail_confirm_count[0] = 0.0
                    trail_candidate[0] = nan

                    # Draw each label inside its own branch. Indie variables
                    # declared inside an indented branch are not visible outside it.
                    if tp_progress >= 0.95:
                        trail_stage[0] = 3.0
                        self.chart.draw(
                            LabelAbs(
                                'ADAPTIVE SL: LOCK 0.60R',
                                AbsolutePosition(self.time[0], sl[0]),
                                font_size=9,
                                text_color=color.BLACK,
                                bg_color=color.TRANSPARENT
                            )
                        )
                    elif tp_progress >= 0.85:
                        trail_stage[0] = 2.0
                        self.chart.draw(
                            LabelAbs(
                                'ADAPTIVE SL: LOCK 0.30R',
                                AbsolutePosition(self.time[0], sl[0]),
                                font_size=9,
                                text_color=color.BLACK,
                                bg_color=color.TRANSPARENT
                            )
                        )
                    elif r_progress >= 1.0:
                        trail_stage[0] = 1.0
                        self.chart.draw(
                            LabelAbs(
                                'ADAPTIVE SL: BREAK EVEN / TRAIL',
                                AbsolutePosition(self.time[0], sl[0]),
                                font_size=9,
                                text_color=color.BLACK,
                                bg_color=color.TRANSPARENT
                            )
                        )
                    else:
                        trail_stage[0] = 4.0
                        self.chart.draw(
                            LabelAbs(
                                'ADAPTIVE SL: STRUCTURE TRAIL',
                                AbsolutePosition(self.time[0], sl[0]),
                                font_size=9,
                                text_color=color.BLACK,
                                bg_color=color.TRANSPARENT
                            )
                        )

                entry[0] = early_leg_entry[0]

            # ================================================
            # EARLY EXIT WARNING
            # ================================================

            if side[0] == 1.0 and early_exit_warned[0] == 0.0:

                buy_failure_score = 0

                if self.close[0] < ema20[0] and ema20[0] < ema50[0]:
                    buy_failure_score += 1

                if htf_sell:
                    buy_failure_score += 1

                if rsi[0] < 45 and rsi[0] < rsi[1]:
                    buy_failure_score += 1

                if bearish_price_action:
                    buy_failure_score += 1

                if buy_failure_score >= 3:

                    early_exit_warned[0] = 1.0

                    if self.is_closed_bar:

                        pass

            elif side[0] == -1.0 and early_exit_warned[0] == 0.0:

                sell_failure_score = 0

                if self.close[0] > ema20[0] and ema20[0] > ema50[0]:
                    sell_failure_score += 1

                if htf_buy:
                    sell_failure_score += 1

                if rsi[0] > 55 and rsi[0] > rsi[1]:
                    sell_failure_score += 1

                if bullish_price_action:
                    sell_failure_score += 1

                if sell_failure_score >= 3:

                    early_exit_warned[0] = 1.0

                    if self.is_closed_bar:

                        pass

            # ================================================
            # ADD-ON ENTRIES 2 TO 5
            # ================================================

            if (
                side[0] != 0.0
                and entry_count[0] >= 1.0
                and entry_count[0] < 5.0
                and self.bar_index > last_entry_bar[0]
            ):

                is_buy_side = side[0] == 1.0

                add_ok = False

                if is_buy_side:

                    add_ok = (
                        candidate_entry_price < last_entry_price[0]
                        and bullish_price_action
                        and buy_add_location
                        and buy_add_score >= 4
                    )

                else:

                    add_ok = (
                        candidate_entry_price > last_entry_price[0]
                        and bearish_price_action
                        and sell_add_location
                        and sell_add_score >= 4
                    )

                if add_ok:

                    new_count = entry_count[0] + 1.0

                    entry_count[0] = new_count
                    last_entry_bar[0] = float(self.bar_index)
                    last_entry_price[0] = candidate_entry_price

                    add_name = 'Second'
                    add_color = color.BLACK

                    if new_count == 2.0:
                        second_entry_price[0] = candidate_entry_price

                    elif new_count == 3.0:
                        third_entry_price[0] = candidate_entry_price
                        add_name = 'Third'
                        add_color = color.FUCHSIA

                    elif new_count == 4.0:
                        fourth_entry_price[0] = candidate_entry_price
                        add_name = 'Fourth'
                        add_color = color.YELLOW

                    else:
                        fifth_entry_price[0] = candidate_entry_price
                        add_name = 'Fifth'
                        add_color = color.PURPLE

                    add_setup_name = add_name + (
                        ' BUY' if is_buy_side else ' SELL'
                    )

                    if not (
                        self.delete_setup == add_setup_name
                        and self.bar_index == self.delete_bar_index
                    ):

                        if is_buy_side:

                            if self.is_closed_bar:

                                pass

                        else:

                            if self.is_closed_bar:

                                pass

            # ================================================
            # ARM NEW BREAKOUT PULLBACK SETUPS
            # ================================================

            if side[0] == 0.0 and not trade_exited:

                if bullish_breakout_volume_setup:

                    pending_buy[0] = 1.0
                    pending_buy_average[0] = (
                        self.high[0] + self.low[0]
                    ) / 2.0
                    pending_buy_low[0] = self.low[0]
                    pending_buy_bar[0] = float(self.bar_index)

                    pending_sell[0] = 0.0
                    pending_sell_average[0] = nan
                    pending_sell_high[0] = nan
                    pending_sell_bar[0] = -1.0

                elif bearish_breakout_volume_setup:

                    pending_sell[0] = 1.0
                    pending_sell_average[0] = (
                        self.high[0] + self.low[0]
                    ) / 2.0
                    pending_sell_high[0] = self.high[0]
                    pending_sell_bar[0] = float(self.bar_index)

                    pending_buy[0] = 0.0
                    pending_buy_average[0] = nan
                    pending_buy_low[0] = nan
                    pending_buy_bar[0] = -1.0

            # ================================================
            # VALIDATE / EXPIRE PENDING BUY SETUP
            # ================================================

            if (
                pending_buy[0] == 1.0
                and self.bar_index > pending_buy_bar[0]
            ):

                buy_pending_age = (
                    self.bar_index - pending_buy_bar[0]
                )

                if (
                    buy_pending_age > 10.0
                    or self.close[0] < pending_buy_low[0]
                ):

                    pending_buy[0] = 0.0
                    pending_buy_average[0] = nan
                    pending_buy_low[0] = nan
                    pending_buy_bar[0] = -1.0

            # ================================================
            # VALIDATE / EXPIRE PENDING SELL SETUP
            # ================================================

            if (
                pending_sell[0] == 1.0
                and self.bar_index > pending_sell_bar[0]
            ):

                sell_pending_age = (
                    self.bar_index - pending_sell_bar[0]
                )

                if (
                    sell_pending_age > 10.0
                    or self.close[0] > pending_sell_high[0]
                ):

                    pending_sell[0] = 0.0
                    pending_sell_average[0] = nan
                    pending_sell_high[0] = nan
                    pending_sell_bar[0] = -1.0

            # ================================================
            # CHECK BUY PULLBACK ENTRY
            # ================================================

            buy_breakout_pullback_ready = False
            buy_breakout_entry_price = nan

            bullish_pullback_confirmation = (
                self.close[0] > self.open[0]
                and (
                    bullish_rejection
                    or bullish_engulfing
                    or bullish_hammer
                    or bullish_close_momentum
                )
            )

            if (
                pending_buy[0] == 1.0
                and self.bar_index > pending_buy_bar[0]
                and bullish_pullback_confirmation
            ):

                buy_average_touched = (
                    self.low[0] <= pending_buy_average[0]
                    and self.close[0] > pending_buy_average[0]
                )

                buy_bottom_touched = (
                    self.low[0] <= pending_buy_low[0]
                    and self.close[0] > pending_buy_low[0]
                )

                if buy_average_touched:

                    buy_breakout_pullback_ready = True
                    buy_breakout_entry_price = pending_buy_average[0]

                elif buy_bottom_touched:

                    buy_breakout_pullback_ready = True
                    buy_breakout_entry_price = pending_buy_low[0]

            # ================================================
            # CHECK SELL PULLBACK ENTRY
            # ================================================

            sell_breakout_pullback_ready = False
            sell_breakout_entry_price = nan

            bearish_pullback_confirmation = (
                self.close[0] < self.open[0]
                and (
                    bearish_rejection
                    or bearish_engulfing
                    or bearish_shooting_star
                    or bearish_close_momentum
                )
            )

            if (
                pending_sell[0] == 1.0
                and self.bar_index > pending_sell_bar[0]
                and bearish_pullback_confirmation
            ):

                sell_average_touched = (
                    self.high[0] >= pending_sell_average[0]
                    and self.close[0] < pending_sell_average[0]
                )

                sell_top_touched = (
                    self.high[0] >= pending_sell_high[0]
                    and self.close[0] < pending_sell_high[0]
                )

                if sell_average_touched:

                    sell_breakout_pullback_ready = True
                    sell_breakout_entry_price = pending_sell_average[0]

                elif sell_top_touched:

                    sell_breakout_pullback_ready = True
                    sell_breakout_entry_price = pending_sell_high[0]

            # ================================================
            # DYNAMIC DAILY RISK BUDGET
            # ================================================

            if reduced_risk_mode[0] == 1.0:
                total_risk_percent = reduced_risk_percent
            else:
                total_risk_percent = normal_risk_percent

            risk_budget_cash = (
                self.account_capital * total_risk_percent / 100.0
            )

            # Independent original-midpoint setup counter.
            # Resolve every outstanding setup independently before arming this bar's setup.
            # SL/TP wins over midpoint if both are touched on the same candle.
            if self.is_closed_bar:
                if count_1_side[0] != 0.0 and self.bar_index > count_1_bar[0]:
                    count_1_entry_touched = (
                        self.low[0] <= count_1_entry[0]
                        if count_1_side[0] == 1.0 else
                        self.high[0] >= count_1_entry[0]
                    )
                    count_1_sl_touched = (
                        self.low[0] <= count_1_sl[0]
                        if count_1_side[0] == 1.0 else
                        self.high[0] >= count_1_sl[0]
                    )
                    count_1_tp_touched = (
                        self.high[0] >= count_1_tp[0]
                        if count_1_side[0] == 1.0 else
                        self.low[0] <= count_1_tp[0]
                    )
                    if count_1_sl_touched or count_1_tp_touched:
                        if count_1_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_1_side[0] = 0.0
                        count_1_entry[0] = nan
                        count_1_sl[0] = nan
                        count_1_tp[0] = nan
                        count_1_day[0] = nan
                        count_1_bar[0] = -1.0
                    elif count_1_entry_touched:
                        if count_1_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_1_side[0] = 0.0
                        count_1_entry[0] = nan
                        count_1_sl[0] = nan
                        count_1_tp[0] = nan
                        count_1_day[0] = nan
                        count_1_bar[0] = -1.0

                if count_2_side[0] != 0.0 and self.bar_index > count_2_bar[0]:
                    count_2_entry_touched = (
                        self.low[0] <= count_2_entry[0]
                        if count_2_side[0] == 1.0 else
                        self.high[0] >= count_2_entry[0]
                    )
                    count_2_sl_touched = (
                        self.low[0] <= count_2_sl[0]
                        if count_2_side[0] == 1.0 else
                        self.high[0] >= count_2_sl[0]
                    )
                    count_2_tp_touched = (
                        self.high[0] >= count_2_tp[0]
                        if count_2_side[0] == 1.0 else
                        self.low[0] <= count_2_tp[0]
                    )
                    if count_2_sl_touched or count_2_tp_touched:
                        if count_2_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_2_side[0] = 0.0
                        count_2_entry[0] = nan
                        count_2_sl[0] = nan
                        count_2_tp[0] = nan
                        count_2_day[0] = nan
                        count_2_bar[0] = -1.0
                    elif count_2_entry_touched:
                        if count_2_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_2_side[0] = 0.0
                        count_2_entry[0] = nan
                        count_2_sl[0] = nan
                        count_2_tp[0] = nan
                        count_2_day[0] = nan
                        count_2_bar[0] = -1.0

                if count_3_side[0] != 0.0 and self.bar_index > count_3_bar[0]:
                    count_3_entry_touched = (
                        self.low[0] <= count_3_entry[0]
                        if count_3_side[0] == 1.0 else
                        self.high[0] >= count_3_entry[0]
                    )
                    count_3_sl_touched = (
                        self.low[0] <= count_3_sl[0]
                        if count_3_side[0] == 1.0 else
                        self.high[0] >= count_3_sl[0]
                    )
                    count_3_tp_touched = (
                        self.high[0] >= count_3_tp[0]
                        if count_3_side[0] == 1.0 else
                        self.low[0] <= count_3_tp[0]
                    )
                    if count_3_sl_touched or count_3_tp_touched:
                        if count_3_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_3_side[0] = 0.0
                        count_3_entry[0] = nan
                        count_3_sl[0] = nan
                        count_3_tp[0] = nan
                        count_3_day[0] = nan
                        count_3_bar[0] = -1.0
                    elif count_3_entry_touched:
                        if count_3_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_3_side[0] = 0.0
                        count_3_entry[0] = nan
                        count_3_sl[0] = nan
                        count_3_tp[0] = nan
                        count_3_day[0] = nan
                        count_3_bar[0] = -1.0

                if count_4_side[0] != 0.0 and self.bar_index > count_4_bar[0]:
                    count_4_entry_touched = (
                        self.low[0] <= count_4_entry[0]
                        if count_4_side[0] == 1.0 else
                        self.high[0] >= count_4_entry[0]
                    )
                    count_4_sl_touched = (
                        self.low[0] <= count_4_sl[0]
                        if count_4_side[0] == 1.0 else
                        self.high[0] >= count_4_sl[0]
                    )
                    count_4_tp_touched = (
                        self.high[0] >= count_4_tp[0]
                        if count_4_side[0] == 1.0 else
                        self.low[0] <= count_4_tp[0]
                    )
                    if count_4_sl_touched or count_4_tp_touched:
                        if count_4_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_4_side[0] = 0.0
                        count_4_entry[0] = nan
                        count_4_sl[0] = nan
                        count_4_tp[0] = nan
                        count_4_day[0] = nan
                        count_4_bar[0] = -1.0
                    elif count_4_entry_touched:
                        if count_4_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_4_side[0] = 0.0
                        count_4_entry[0] = nan
                        count_4_sl[0] = nan
                        count_4_tp[0] = nan
                        count_4_day[0] = nan
                        count_4_bar[0] = -1.0

                if count_5_side[0] != 0.0 and self.bar_index > count_5_bar[0]:
                    count_5_entry_touched = (
                        self.low[0] <= count_5_entry[0]
                        if count_5_side[0] == 1.0 else
                        self.high[0] >= count_5_entry[0]
                    )
                    count_5_sl_touched = (
                        self.low[0] <= count_5_sl[0]
                        if count_5_side[0] == 1.0 else
                        self.high[0] >= count_5_sl[0]
                    )
                    count_5_tp_touched = (
                        self.high[0] >= count_5_tp[0]
                        if count_5_side[0] == 1.0 else
                        self.low[0] <= count_5_tp[0]
                    )
                    if count_5_sl_touched or count_5_tp_touched:
                        if count_5_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_5_side[0] = 0.0
                        count_5_entry[0] = nan
                        count_5_sl[0] = nan
                        count_5_tp[0] = nan
                        count_5_day[0] = nan
                        count_5_bar[0] = -1.0
                    elif count_5_entry_touched:
                        if count_5_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_5_side[0] = 0.0
                        count_5_entry[0] = nan
                        count_5_sl[0] = nan
                        count_5_tp[0] = nan
                        count_5_day[0] = nan
                        count_5_bar[0] = -1.0

                if count_6_side[0] != 0.0 and self.bar_index > count_6_bar[0]:
                    count_6_entry_touched = (
                        self.low[0] <= count_6_entry[0]
                        if count_6_side[0] == 1.0 else
                        self.high[0] >= count_6_entry[0]
                    )
                    count_6_sl_touched = (
                        self.low[0] <= count_6_sl[0]
                        if count_6_side[0] == 1.0 else
                        self.high[0] >= count_6_sl[0]
                    )
                    count_6_tp_touched = (
                        self.high[0] >= count_6_tp[0]
                        if count_6_side[0] == 1.0 else
                        self.low[0] <= count_6_tp[0]
                    )
                    if count_6_sl_touched or count_6_tp_touched:
                        if count_6_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_6_side[0] = 0.0
                        count_6_entry[0] = nan
                        count_6_sl[0] = nan
                        count_6_tp[0] = nan
                        count_6_day[0] = nan
                        count_6_bar[0] = -1.0
                    elif count_6_entry_touched:
                        if count_6_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_6_side[0] = 0.0
                        count_6_entry[0] = nan
                        count_6_sl[0] = nan
                        count_6_tp[0] = nan
                        count_6_day[0] = nan
                        count_6_bar[0] = -1.0

                if count_7_side[0] != 0.0 and self.bar_index > count_7_bar[0]:
                    count_7_entry_touched = (
                        self.low[0] <= count_7_entry[0]
                        if count_7_side[0] == 1.0 else
                        self.high[0] >= count_7_entry[0]
                    )
                    count_7_sl_touched = (
                        self.low[0] <= count_7_sl[0]
                        if count_7_side[0] == 1.0 else
                        self.high[0] >= count_7_sl[0]
                    )
                    count_7_tp_touched = (
                        self.high[0] >= count_7_tp[0]
                        if count_7_side[0] == 1.0 else
                        self.low[0] <= count_7_tp[0]
                    )
                    if count_7_sl_touched or count_7_tp_touched:
                        if count_7_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_7_side[0] = 0.0
                        count_7_entry[0] = nan
                        count_7_sl[0] = nan
                        count_7_tp[0] = nan
                        count_7_day[0] = nan
                        count_7_bar[0] = -1.0
                    elif count_7_entry_touched:
                        if count_7_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_7_side[0] = 0.0
                        count_7_entry[0] = nan
                        count_7_sl[0] = nan
                        count_7_tp[0] = nan
                        count_7_day[0] = nan
                        count_7_bar[0] = -1.0

                if count_8_side[0] != 0.0 and self.bar_index > count_8_bar[0]:
                    count_8_entry_touched = (
                        self.low[0] <= count_8_entry[0]
                        if count_8_side[0] == 1.0 else
                        self.high[0] >= count_8_entry[0]
                    )
                    count_8_sl_touched = (
                        self.low[0] <= count_8_sl[0]
                        if count_8_side[0] == 1.0 else
                        self.high[0] >= count_8_sl[0]
                    )
                    count_8_tp_touched = (
                        self.high[0] >= count_8_tp[0]
                        if count_8_side[0] == 1.0 else
                        self.low[0] <= count_8_tp[0]
                    )
                    if count_8_sl_touched or count_8_tp_touched:
                        if count_8_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_8_side[0] = 0.0
                        count_8_entry[0] = nan
                        count_8_sl[0] = nan
                        count_8_tp[0] = nan
                        count_8_day[0] = nan
                        count_8_bar[0] = -1.0
                    elif count_8_entry_touched:
                        if count_8_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_8_side[0] = 0.0
                        count_8_entry[0] = nan
                        count_8_sl[0] = nan
                        count_8_tp[0] = nan
                        count_8_day[0] = nan
                        count_8_bar[0] = -1.0

                if count_9_side[0] != 0.0 and self.bar_index > count_9_bar[0]:
                    count_9_entry_touched = (
                        self.low[0] <= count_9_entry[0]
                        if count_9_side[0] == 1.0 else
                        self.high[0] >= count_9_entry[0]
                    )
                    count_9_sl_touched = (
                        self.low[0] <= count_9_sl[0]
                        if count_9_side[0] == 1.0 else
                        self.high[0] >= count_9_sl[0]
                    )
                    count_9_tp_touched = (
                        self.high[0] >= count_9_tp[0]
                        if count_9_side[0] == 1.0 else
                        self.low[0] <= count_9_tp[0]
                    )
                    if count_9_sl_touched or count_9_tp_touched:
                        if count_9_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_9_side[0] = 0.0
                        count_9_entry[0] = nan
                        count_9_sl[0] = nan
                        count_9_tp[0] = nan
                        count_9_day[0] = nan
                        count_9_bar[0] = -1.0
                    elif count_9_entry_touched:
                        if count_9_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_9_side[0] = 0.0
                        count_9_entry[0] = nan
                        count_9_sl[0] = nan
                        count_9_tp[0] = nan
                        count_9_day[0] = nan
                        count_9_bar[0] = -1.0

                if count_10_side[0] != 0.0 and self.bar_index > count_10_bar[0]:
                    count_10_entry_touched = (
                        self.low[0] <= count_10_entry[0]
                        if count_10_side[0] == 1.0 else
                        self.high[0] >= count_10_entry[0]
                    )
                    count_10_sl_touched = (
                        self.low[0] <= count_10_sl[0]
                        if count_10_side[0] == 1.0 else
                        self.high[0] >= count_10_sl[0]
                    )
                    count_10_tp_touched = (
                        self.high[0] >= count_10_tp[0]
                        if count_10_side[0] == 1.0 else
                        self.low[0] <= count_10_tp[0]
                    )
                    if count_10_sl_touched or count_10_tp_touched:
                        if count_10_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_10_side[0] = 0.0
                        count_10_entry[0] = nan
                        count_10_sl[0] = nan
                        count_10_tp[0] = nan
                        count_10_day[0] = nan
                        count_10_bar[0] = -1.0
                    elif count_10_entry_touched:
                        if count_10_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_10_side[0] = 0.0
                        count_10_entry[0] = nan
                        count_10_sl[0] = nan
                        count_10_tp[0] = nan
                        count_10_day[0] = nan
                        count_10_bar[0] = -1.0

                if count_11_side[0] != 0.0 and self.bar_index > count_11_bar[0]:
                    count_11_entry_touched = (
                        self.low[0] <= count_11_entry[0]
                        if count_11_side[0] == 1.0 else
                        self.high[0] >= count_11_entry[0]
                    )
                    count_11_sl_touched = (
                        self.low[0] <= count_11_sl[0]
                        if count_11_side[0] == 1.0 else
                        self.high[0] >= count_11_sl[0]
                    )
                    count_11_tp_touched = (
                        self.high[0] >= count_11_tp[0]
                        if count_11_side[0] == 1.0 else
                        self.low[0] <= count_11_tp[0]
                    )
                    if count_11_sl_touched or count_11_tp_touched:
                        if count_11_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_11_side[0] = 0.0
                        count_11_entry[0] = nan
                        count_11_sl[0] = nan
                        count_11_tp[0] = nan
                        count_11_day[0] = nan
                        count_11_bar[0] = -1.0
                    elif count_11_entry_touched:
                        if count_11_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_11_side[0] = 0.0
                        count_11_entry[0] = nan
                        count_11_sl[0] = nan
                        count_11_tp[0] = nan
                        count_11_day[0] = nan
                        count_11_bar[0] = -1.0

                if count_12_side[0] != 0.0 and self.bar_index > count_12_bar[0]:
                    count_12_entry_touched = (
                        self.low[0] <= count_12_entry[0]
                        if count_12_side[0] == 1.0 else
                        self.high[0] >= count_12_entry[0]
                    )
                    count_12_sl_touched = (
                        self.low[0] <= count_12_sl[0]
                        if count_12_side[0] == 1.0 else
                        self.high[0] >= count_12_sl[0]
                    )
                    count_12_tp_touched = (
                        self.high[0] >= count_12_tp[0]
                        if count_12_side[0] == 1.0 else
                        self.low[0] <= count_12_tp[0]
                    )
                    if count_12_sl_touched or count_12_tp_touched:
                        if count_12_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_12_side[0] = 0.0
                        count_12_entry[0] = nan
                        count_12_sl[0] = nan
                        count_12_tp[0] = nan
                        count_12_day[0] = nan
                        count_12_bar[0] = -1.0
                    elif count_12_entry_touched:
                        if count_12_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_12_side[0] = 0.0
                        count_12_entry[0] = nan
                        count_12_sl[0] = nan
                        count_12_tp[0] = nan
                        count_12_day[0] = nan
                        count_12_bar[0] = -1.0

                if count_13_side[0] != 0.0 and self.bar_index > count_13_bar[0]:
                    count_13_entry_touched = (
                        self.low[0] <= count_13_entry[0]
                        if count_13_side[0] == 1.0 else
                        self.high[0] >= count_13_entry[0]
                    )
                    count_13_sl_touched = (
                        self.low[0] <= count_13_sl[0]
                        if count_13_side[0] == 1.0 else
                        self.high[0] >= count_13_sl[0]
                    )
                    count_13_tp_touched = (
                        self.high[0] >= count_13_tp[0]
                        if count_13_side[0] == 1.0 else
                        self.low[0] <= count_13_tp[0]
                    )
                    if count_13_sl_touched or count_13_tp_touched:
                        if count_13_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_13_side[0] = 0.0
                        count_13_entry[0] = nan
                        count_13_sl[0] = nan
                        count_13_tp[0] = nan
                        count_13_day[0] = nan
                        count_13_bar[0] = -1.0
                    elif count_13_entry_touched:
                        if count_13_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_13_side[0] = 0.0
                        count_13_entry[0] = nan
                        count_13_sl[0] = nan
                        count_13_tp[0] = nan
                        count_13_day[0] = nan
                        count_13_bar[0] = -1.0

                if count_14_side[0] != 0.0 and self.bar_index > count_14_bar[0]:
                    count_14_entry_touched = (
                        self.low[0] <= count_14_entry[0]
                        if count_14_side[0] == 1.0 else
                        self.high[0] >= count_14_entry[0]
                    )
                    count_14_sl_touched = (
                        self.low[0] <= count_14_sl[0]
                        if count_14_side[0] == 1.0 else
                        self.high[0] >= count_14_sl[0]
                    )
                    count_14_tp_touched = (
                        self.high[0] >= count_14_tp[0]
                        if count_14_side[0] == 1.0 else
                        self.low[0] <= count_14_tp[0]
                    )
                    if count_14_sl_touched or count_14_tp_touched:
                        if count_14_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_14_side[0] = 0.0
                        count_14_entry[0] = nan
                        count_14_sl[0] = nan
                        count_14_tp[0] = nan
                        count_14_day[0] = nan
                        count_14_bar[0] = -1.0
                    elif count_14_entry_touched:
                        if count_14_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_14_side[0] = 0.0
                        count_14_entry[0] = nan
                        count_14_sl[0] = nan
                        count_14_tp[0] = nan
                        count_14_day[0] = nan
                        count_14_bar[0] = -1.0

                if count_15_side[0] != 0.0 and self.bar_index > count_15_bar[0]:
                    count_15_entry_touched = (
                        self.low[0] <= count_15_entry[0]
                        if count_15_side[0] == 1.0 else
                        self.high[0] >= count_15_entry[0]
                    )
                    count_15_sl_touched = (
                        self.low[0] <= count_15_sl[0]
                        if count_15_side[0] == 1.0 else
                        self.high[0] >= count_15_sl[0]
                    )
                    count_15_tp_touched = (
                        self.high[0] >= count_15_tp[0]
                        if count_15_side[0] == 1.0 else
                        self.low[0] <= count_15_tp[0]
                    )
                    if count_15_sl_touched or count_15_tp_touched:
                        if count_15_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_15_side[0] = 0.0
                        count_15_entry[0] = nan
                        count_15_sl[0] = nan
                        count_15_tp[0] = nan
                        count_15_day[0] = nan
                        count_15_bar[0] = -1.0
                    elif count_15_entry_touched:
                        if count_15_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_15_side[0] = 0.0
                        count_15_entry[0] = nan
                        count_15_sl[0] = nan
                        count_15_tp[0] = nan
                        count_15_day[0] = nan
                        count_15_bar[0] = -1.0

                if count_16_side[0] != 0.0 and self.bar_index > count_16_bar[0]:
                    count_16_entry_touched = (
                        self.low[0] <= count_16_entry[0]
                        if count_16_side[0] == 1.0 else
                        self.high[0] >= count_16_entry[0]
                    )
                    count_16_sl_touched = (
                        self.low[0] <= count_16_sl[0]
                        if count_16_side[0] == 1.0 else
                        self.high[0] >= count_16_sl[0]
                    )
                    count_16_tp_touched = (
                        self.high[0] >= count_16_tp[0]
                        if count_16_side[0] == 1.0 else
                        self.low[0] <= count_16_tp[0]
                    )
                    if count_16_sl_touched or count_16_tp_touched:
                        if count_16_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_16_side[0] = 0.0
                        count_16_entry[0] = nan
                        count_16_sl[0] = nan
                        count_16_tp[0] = nan
                        count_16_day[0] = nan
                        count_16_bar[0] = -1.0
                    elif count_16_entry_touched:
                        if count_16_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_16_side[0] = 0.0
                        count_16_entry[0] = nan
                        count_16_sl[0] = nan
                        count_16_tp[0] = nan
                        count_16_day[0] = nan
                        count_16_bar[0] = -1.0

                if count_17_side[0] != 0.0 and self.bar_index > count_17_bar[0]:
                    count_17_entry_touched = (
                        self.low[0] <= count_17_entry[0]
                        if count_17_side[0] == 1.0 else
                        self.high[0] >= count_17_entry[0]
                    )
                    count_17_sl_touched = (
                        self.low[0] <= count_17_sl[0]
                        if count_17_side[0] == 1.0 else
                        self.high[0] >= count_17_sl[0]
                    )
                    count_17_tp_touched = (
                        self.high[0] >= count_17_tp[0]
                        if count_17_side[0] == 1.0 else
                        self.low[0] <= count_17_tp[0]
                    )
                    if count_17_sl_touched or count_17_tp_touched:
                        if count_17_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_17_side[0] = 0.0
                        count_17_entry[0] = nan
                        count_17_sl[0] = nan
                        count_17_tp[0] = nan
                        count_17_day[0] = nan
                        count_17_bar[0] = -1.0
                    elif count_17_entry_touched:
                        if count_17_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_17_side[0] = 0.0
                        count_17_entry[0] = nan
                        count_17_sl[0] = nan
                        count_17_tp[0] = nan
                        count_17_day[0] = nan
                        count_17_bar[0] = -1.0

                if count_18_side[0] != 0.0 and self.bar_index > count_18_bar[0]:
                    count_18_entry_touched = (
                        self.low[0] <= count_18_entry[0]
                        if count_18_side[0] == 1.0 else
                        self.high[0] >= count_18_entry[0]
                    )
                    count_18_sl_touched = (
                        self.low[0] <= count_18_sl[0]
                        if count_18_side[0] == 1.0 else
                        self.high[0] >= count_18_sl[0]
                    )
                    count_18_tp_touched = (
                        self.high[0] >= count_18_tp[0]
                        if count_18_side[0] == 1.0 else
                        self.low[0] <= count_18_tp[0]
                    )
                    if count_18_sl_touched or count_18_tp_touched:
                        if count_18_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_18_side[0] = 0.0
                        count_18_entry[0] = nan
                        count_18_sl[0] = nan
                        count_18_tp[0] = nan
                        count_18_day[0] = nan
                        count_18_bar[0] = -1.0
                    elif count_18_entry_touched:
                        if count_18_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_18_side[0] = 0.0
                        count_18_entry[0] = nan
                        count_18_sl[0] = nan
                        count_18_tp[0] = nan
                        count_18_day[0] = nan
                        count_18_bar[0] = -1.0

                if count_19_side[0] != 0.0 and self.bar_index > count_19_bar[0]:
                    count_19_entry_touched = (
                        self.low[0] <= count_19_entry[0]
                        if count_19_side[0] == 1.0 else
                        self.high[0] >= count_19_entry[0]
                    )
                    count_19_sl_touched = (
                        self.low[0] <= count_19_sl[0]
                        if count_19_side[0] == 1.0 else
                        self.high[0] >= count_19_sl[0]
                    )
                    count_19_tp_touched = (
                        self.high[0] >= count_19_tp[0]
                        if count_19_side[0] == 1.0 else
                        self.low[0] <= count_19_tp[0]
                    )
                    if count_19_sl_touched or count_19_tp_touched:
                        if count_19_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_19_side[0] = 0.0
                        count_19_entry[0] = nan
                        count_19_sl[0] = nan
                        count_19_tp[0] = nan
                        count_19_day[0] = nan
                        count_19_bar[0] = -1.0
                    elif count_19_entry_touched:
                        if count_19_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_19_side[0] = 0.0
                        count_19_entry[0] = nan
                        count_19_sl[0] = nan
                        count_19_tp[0] = nan
                        count_19_day[0] = nan
                        count_19_bar[0] = -1.0

                if count_20_side[0] != 0.0 and self.bar_index > count_20_bar[0]:
                    count_20_entry_touched = (
                        self.low[0] <= count_20_entry[0]
                        if count_20_side[0] == 1.0 else
                        self.high[0] >= count_20_entry[0]
                    )
                    count_20_sl_touched = (
                        self.low[0] <= count_20_sl[0]
                        if count_20_side[0] == 1.0 else
                        self.high[0] >= count_20_sl[0]
                    )
                    count_20_tp_touched = (
                        self.high[0] >= count_20_tp[0]
                        if count_20_side[0] == 1.0 else
                        self.low[0] <= count_20_tp[0]
                    )
                    if count_20_sl_touched or count_20_tp_touched:
                        if count_20_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_20_side[0] = 0.0
                        count_20_entry[0] = nan
                        count_20_sl[0] = nan
                        count_20_tp[0] = nan
                        count_20_day[0] = nan
                        count_20_bar[0] = -1.0
                    elif count_20_entry_touched:
                        if count_20_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_20_side[0] = 0.0
                        count_20_entry[0] = nan
                        count_20_sl[0] = nan
                        count_20_tp[0] = nan
                        count_20_day[0] = nan
                        count_20_bar[0] = -1.0

                if not rr_setting_changed:
                    count_sell_ready = sell_condition or sell_breakout_pullback_ready
                    count_buy_ready = buy_condition or buy_breakout_pullback_ready

                    if count_sell_ready and not count_buy_ready:
                        count_new_entry = candidate_entry_price
                        count_recent_high = max([
                            self.high[0], self.high[1], self.high[2], self.high[3],
                            self.high[4], self.high[5], self.high[6], self.high[7]
                        ])
                        count_stop_buffer = max(candle_range * 0.25, abs(count_new_entry) * 0.00005)
                        count_new_stop = max(count_recent_high, count_new_entry + count_stop_buffer)
                        count_new_risk = count_new_stop - count_new_entry
                        count_new_distance = abs(count_new_entry - count_new_stop)
                        count_new_side = -1.0
                    elif count_buy_ready:
                        count_new_entry = candidate_entry_price
                        count_recent_low = min([
                            self.low[0], self.low[1], self.low[2], self.low[3],
                            self.low[4], self.low[5], self.low[6], self.low[7]
                        ])
                        count_stop_buffer = max(candle_range * 0.25, abs(count_new_entry) * 0.00005)
                        count_new_stop = min(count_recent_low, count_new_entry - count_stop_buffer)
                        count_new_risk = count_new_entry - count_new_stop
                        count_new_distance = abs(count_new_entry - count_new_stop)
                        count_new_side = 1.0
                    else:
                        count_new_risk = 0.0
                        count_new_distance = 0.0

                    count_new_risk_per_lot = count_new_distance * self.contract_size
                    count_new_lot = 0.0
                    if count_new_risk_per_lot > 0.0 and risk_budget_cash > 0.0:
                        count_new_lot = int((risk_budget_cash / count_new_risk_per_lot) * 100.0) / 100.0

                    if (
                        count_new_side != 0.0
                        and count_new_risk > 0.0
                        and count_new_distance <= maximum_allowed_sl_distance
                        and count_new_lot >= 0.01
                    ):
                        if count_1_side[0] == 0.0:
                            count_1_side[0] = count_new_side
                            count_1_entry[0] = count_new_entry
                            count_1_sl[0] = count_new_stop
                            count_1_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_1_day[0] = current_ist_day_key
                            count_1_bar[0] = float(self.bar_index)
                        elif count_2_side[0] == 0.0:
                            count_2_side[0] = count_new_side
                            count_2_entry[0] = count_new_entry
                            count_2_sl[0] = count_new_stop
                            count_2_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_2_day[0] = current_ist_day_key
                            count_2_bar[0] = float(self.bar_index)
                        elif count_3_side[0] == 0.0:
                            count_3_side[0] = count_new_side
                            count_3_entry[0] = count_new_entry
                            count_3_sl[0] = count_new_stop
                            count_3_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_3_day[0] = current_ist_day_key
                            count_3_bar[0] = float(self.bar_index)
                        elif count_4_side[0] == 0.0:
                            count_4_side[0] = count_new_side
                            count_4_entry[0] = count_new_entry
                            count_4_sl[0] = count_new_stop
                            count_4_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_4_day[0] = current_ist_day_key
                            count_4_bar[0] = float(self.bar_index)
                        elif count_5_side[0] == 0.0:
                            count_5_side[0] = count_new_side
                            count_5_entry[0] = count_new_entry
                            count_5_sl[0] = count_new_stop
                            count_5_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_5_day[0] = current_ist_day_key
                            count_5_bar[0] = float(self.bar_index)
                        elif count_6_side[0] == 0.0:
                            count_6_side[0] = count_new_side
                            count_6_entry[0] = count_new_entry
                            count_6_sl[0] = count_new_stop
                            count_6_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_6_day[0] = current_ist_day_key
                            count_6_bar[0] = float(self.bar_index)
                        elif count_7_side[0] == 0.0:
                            count_7_side[0] = count_new_side
                            count_7_entry[0] = count_new_entry
                            count_7_sl[0] = count_new_stop
                            count_7_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_7_day[0] = current_ist_day_key
                            count_7_bar[0] = float(self.bar_index)
                        elif count_8_side[0] == 0.0:
                            count_8_side[0] = count_new_side
                            count_8_entry[0] = count_new_entry
                            count_8_sl[0] = count_new_stop
                            count_8_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_8_day[0] = current_ist_day_key
                            count_8_bar[0] = float(self.bar_index)
                        elif count_9_side[0] == 0.0:
                            count_9_side[0] = count_new_side
                            count_9_entry[0] = count_new_entry
                            count_9_sl[0] = count_new_stop
                            count_9_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_9_day[0] = current_ist_day_key
                            count_9_bar[0] = float(self.bar_index)
                        elif count_10_side[0] == 0.0:
                            count_10_side[0] = count_new_side
                            count_10_entry[0] = count_new_entry
                            count_10_sl[0] = count_new_stop
                            count_10_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_10_day[0] = current_ist_day_key
                            count_10_bar[0] = float(self.bar_index)
                        elif count_11_side[0] == 0.0:
                            count_11_side[0] = count_new_side
                            count_11_entry[0] = count_new_entry
                            count_11_sl[0] = count_new_stop
                            count_11_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_11_day[0] = current_ist_day_key
                            count_11_bar[0] = float(self.bar_index)
                        elif count_12_side[0] == 0.0:
                            count_12_side[0] = count_new_side
                            count_12_entry[0] = count_new_entry
                            count_12_sl[0] = count_new_stop
                            count_12_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_12_day[0] = current_ist_day_key
                            count_12_bar[0] = float(self.bar_index)
                        elif count_13_side[0] == 0.0:
                            count_13_side[0] = count_new_side
                            count_13_entry[0] = count_new_entry
                            count_13_sl[0] = count_new_stop
                            count_13_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_13_day[0] = current_ist_day_key
                            count_13_bar[0] = float(self.bar_index)
                        elif count_14_side[0] == 0.0:
                            count_14_side[0] = count_new_side
                            count_14_entry[0] = count_new_entry
                            count_14_sl[0] = count_new_stop
                            count_14_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_14_day[0] = current_ist_day_key
                            count_14_bar[0] = float(self.bar_index)
                        elif count_15_side[0] == 0.0:
                            count_15_side[0] = count_new_side
                            count_15_entry[0] = count_new_entry
                            count_15_sl[0] = count_new_stop
                            count_15_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_15_day[0] = current_ist_day_key
                            count_15_bar[0] = float(self.bar_index)
                        elif count_16_side[0] == 0.0:
                            count_16_side[0] = count_new_side
                            count_16_entry[0] = count_new_entry
                            count_16_sl[0] = count_new_stop
                            count_16_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_16_day[0] = current_ist_day_key
                            count_16_bar[0] = float(self.bar_index)
                        elif count_17_side[0] == 0.0:
                            count_17_side[0] = count_new_side
                            count_17_entry[0] = count_new_entry
                            count_17_sl[0] = count_new_stop
                            count_17_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_17_day[0] = current_ist_day_key
                            count_17_bar[0] = float(self.bar_index)
                        elif count_18_side[0] == 0.0:
                            count_18_side[0] = count_new_side
                            count_18_entry[0] = count_new_entry
                            count_18_sl[0] = count_new_stop
                            count_18_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_18_day[0] = current_ist_day_key
                            count_18_bar[0] = float(self.bar_index)
                        elif count_19_side[0] == 0.0:
                            count_19_side[0] = count_new_side
                            count_19_entry[0] = count_new_entry
                            count_19_sl[0] = count_new_stop
                            count_19_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_19_day[0] = current_ist_day_key
                            count_19_bar[0] = float(self.bar_index)
                        elif count_20_side[0] == 0.0:
                            count_20_side[0] = count_new_side
                            count_20_entry[0] = count_new_entry
                            count_20_sl[0] = count_new_stop
                            count_20_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_20_day[0] = current_ist_day_key
                            count_20_bar[0] = float(self.bar_index)
                        # If all 20 slots are occupied, do not overwrite an unresolved setup.
            # ================================================
            # NEW PRIMARY ENTRY
            # ================================================

            # Never commit an entry, set active trade state, or expose an
            # absolute entry marker while this candle is still forming.
            # Setup conditions may develop intrabar, but the final entry/SL/TP
            # calculation is committed only on the candle-close callback.
            if (
                self.is_closed_bar and side[0] == 0.0
                and pending_trade_side[0] == 0.0 and not trade_exited
            ):

                # Preserve the original signal conditions without a deviation
                # filter. Entry 1 uses the confirmation candle midpoint.
                sell_entry_ready = sell_condition or sell_breakout_pullback_ready
                buy_entry_ready = buy_condition or buy_breakout_pullback_ready

                if sell_entry_ready and not buy_entry_ready:

                    recent_high = max([
                        self.high[0], self.high[1],
                        self.high[2], self.high[3],
                        self.high[4], self.high[5],
                        self.high[6], self.high[7]
                    ])

                    # Preserve the original midpoint setup and sizing exactly.
                    # The midpoint determines the original SL, TP and total lot.
                    entry_price = candidate_entry_price

                    if sell_breakout_pullback_ready:
                        sell_reason = 'BREAKOUT + VOLUME PULLBACK'

                    stop_price = recent_high
                    entry_stop_buffer = max(
                        candle_range * 0.25,
                        abs(entry_price) * 0.00005
                    )
                    stop_price = max(
                        stop_price,
                        entry_price + entry_stop_buffer
                    )

                    risk = stop_price - entry_price
                    sl_distance = abs(entry_price - stop_price)
                    risk_per_one_lot = sl_distance * self.contract_size
                    calculated_lot = 0.0
                    calculated_risk_cash = nan

                    if risk_per_one_lot > 0.0 and risk_budget_cash > 0.0:
                        raw_lot = risk_budget_cash / risk_per_one_lot
                        calculated_lot = int(raw_lot * 100.0) / 100.0
                        calculated_risk_cash = (
                            calculated_lot * risk_per_one_lot
                        )

                    # Allocate half of the dollar risk budget to the midpoint leg.
                    # The remaining budget is reserved for the immediate leg after midpoint fill.
                    midpoint_risk_per_lot = sl_distance * self.contract_size
                    mid_lot = 0.0
                    if midpoint_risk_per_lot > 0.0 and risk_budget_cash > 0.0:
                        midpoint_half_budget = risk_budget_cash * 0.50
                        mid_lot = int((midpoint_half_budget / midpoint_risk_per_lot) * 100.0) / 100.0

                    mid_risk_cash_value = mid_lot * midpoint_risk_per_lot

                    if (
                        risk > 0.0
                        and sl_distance <= maximum_allowed_sl_distance
                        and mid_lot >= 0.01
                        and mid_risk_cash_value <= risk_budget_cash
                    ):
                        target_price = entry_price - risk * rr_multiplier

                        # Arm only a pending midpoint order. No active side,
                        # trade P/L, or immediate entry is recorded yet.
                        pending_trade_side[0] = -1.0
                        pending_trade_entry[0] = entry_price
                        pending_mid_entry[0] = entry_price
                        pending_trade_sl[0] = stop_price
                        pending_trade_tp[0] = target_price
                        pending_trade_lot[0] = mid_lot
                        pending_trade_risk_cash[0] = mid_risk_cash_value
                        pending_trade_setup_day[0] = current_ist_day_key
                        pending_trade_setup_bar[0] = float(self.bar_index)

                        entry[0] = nan
                        midpoint_master_entry[0] = entry_price
                        early_leg_entry[0] = entry_price
                        early_leg_lot[0] = 0.0
                        mid_leg_lot[0] = mid_lot
                        mid_leg_active[0] = 0.0
                        early_leg_closed[0] = 0.0
                        early_leg_pnl[0] = 0.0
                        mid_leg_pnl[0] = 0.0
                        setup_risk_budget[0] = risk_budget_cash
                        sl[0] = stop_price
                        tp[0] = target_price
                        side[0] = 0.0
                        trade_lot[0] = nan
                        trade_risk_cash[0] = nan
                        original_risk_distance[0] = sl_distance
                        favorable_extreme[0] = entry_price
                        trail_candidate[0] = nan
                        trail_confirm_count[0] = 0.0
                        trail_stage[0] = 0.0
                        trail_last_update_bar[0] = -1.0
                        early_exit_warned[0] = 0.0
                        entry_count[0] = 0.0
                        last_entry_bar[0] = -1.0
                        last_entry_price[0] = nan
                        entry_label_time[0] = self.time[0]
                        pending_early_entry[0] = nan
                        sell_signal = True

                        pending_buy[0] = 0.0
                        pending_buy_average[0] = nan
                        pending_buy_low[0] = nan
                        pending_buy_bar[0] = -1.0
                        pending_sell[0] = 0.0
                        pending_sell_average[0] = nan
                        pending_sell_high[0] = nan
                        pending_sell_bar[0] = -1.0

                elif buy_entry_ready:

                    recent_low = min([
                        self.low[0], self.low[1],
                        self.low[2], self.low[3],
                        self.low[4], self.low[5],
                        self.low[6], self.low[7]
                    ])

                    # Preserve the original midpoint setup and sizing exactly.
                    # The midpoint determines the original SL, TP and total lot.
                    entry_price = candidate_entry_price

                    if buy_breakout_pullback_ready:
                        buy_reason = 'BREAKOUT + VOLUME PULLBACK'

                    stop_price = recent_low
                    entry_stop_buffer = max(
                        candle_range * 0.25,
                        abs(entry_price) * 0.00005
                    )
                    stop_price = min(
                        stop_price,
                        entry_price - entry_stop_buffer
                    )

                    risk = entry_price - stop_price
                    sl_distance = abs(entry_price - stop_price)
                    risk_per_one_lot = sl_distance * self.contract_size
                    calculated_lot = 0.0
                    calculated_risk_cash = nan

                    if risk_per_one_lot > 0.0 and risk_budget_cash > 0.0:
                        raw_lot = risk_budget_cash / risk_per_one_lot
                        calculated_lot = int(raw_lot * 100.0) / 100.0
                        calculated_risk_cash = (
                            calculated_lot * risk_per_one_lot
                        )

                    # Allocate half of the dollar risk budget to the midpoint leg.
                    # The remaining budget is reserved for the immediate leg after midpoint fill.
                    midpoint_risk_per_lot = sl_distance * self.contract_size
                    mid_lot = 0.0
                    if midpoint_risk_per_lot > 0.0 and risk_budget_cash > 0.0:
                        midpoint_half_budget = risk_budget_cash * 0.50
                        mid_lot = int((midpoint_half_budget / midpoint_risk_per_lot) * 100.0) / 100.0

                    mid_risk_cash_value = mid_lot * midpoint_risk_per_lot

                    if (
                        risk > 0.0
                        and sl_distance <= maximum_allowed_sl_distance
                        and mid_lot >= 0.01
                        and mid_risk_cash_value <= risk_budget_cash
                    ):
                        target_price = entry_price + risk * rr_multiplier

                        # Arm only a pending midpoint order. No active side,
                        # trade P/L, or immediate entry is recorded yet.
                        pending_trade_side[0] = 1.0
                        pending_trade_entry[0] = entry_price
                        pending_mid_entry[0] = entry_price
                        pending_trade_sl[0] = stop_price
                        pending_trade_tp[0] = target_price
                        pending_trade_lot[0] = mid_lot
                        pending_trade_risk_cash[0] = mid_risk_cash_value
                        pending_trade_setup_day[0] = current_ist_day_key
                        pending_trade_setup_bar[0] = float(self.bar_index)

                        entry[0] = nan
                        midpoint_master_entry[0] = entry_price
                        early_leg_entry[0] = entry_price
                        early_leg_lot[0] = 0.0
                        mid_leg_lot[0] = mid_lot
                        mid_leg_active[0] = 0.0
                        early_leg_closed[0] = 0.0
                        early_leg_pnl[0] = 0.0
                        mid_leg_pnl[0] = 0.0
                        setup_risk_budget[0] = risk_budget_cash
                        sl[0] = stop_price
                        tp[0] = target_price
                        side[0] = 0.0
                        trade_lot[0] = nan
                        trade_risk_cash[0] = nan
                        original_risk_distance[0] = sl_distance
                        favorable_extreme[0] = entry_price
                        trail_candidate[0] = nan
                        trail_confirm_count[0] = 0.0
                        trail_stage[0] = 0.0
                        trail_last_update_bar[0] = -1.0
                        early_exit_warned[0] = 0.0
                        entry_count[0] = 0.0
                        last_entry_bar[0] = -1.0
                        last_entry_price[0] = nan
                        entry_label_time[0] = self.time[0]
                        pending_early_entry[0] = nan
                        buy_signal = True

                        pending_buy[0] = 0.0
                        pending_buy_average[0] = nan
                        pending_buy_low[0] = nan
                        pending_buy_bar[0] = -1.0
                        pending_sell[0] = 0.0
                        pending_sell_average[0] = nan
                        pending_sell_high[0] = nan
                        pending_sell_bar[0] = -1.0

                        if not (
                            self.delete_setup == 'Primary BUY'
                            and self.bar_index == self.delete_bar_index
                        ):

                            if self.is_closed_bar:

                                pass

        # ====================================================
        # ONE COMBINED TRADE DESCRIPTION BOX
        # ====================================================

        new_trade_entry_event = (
            last_entry_bar[0] == self.bar_index
        )

        # ====================================================
        # LOT LABEL ONLY AT TRADE ENTRY
        # PROFIT / LOSS LABELS ARE DRAWN ONLY AFTER EXIT
        # ====================================================

        if (
            self.show_entry_descriptions
            and new_trade_entry_event
            and side[0] != 0.0
        ):

            is_buy = side[0] == 1.0

            trade_symbol = ''

            entry1_description_reason = (
                buy_reason if is_buy else sell_reason
            )

            entry2_description_reason = ''
            addon_zone_reason = ''

            if is_buy:

                if bullish_breakout_volume_setup or buy_reason == 'BREAKOUT + VOLUME PULLBACK':
                    entry2_description_reason = 'Breakout Pullback'

                elif bullish_engulfing:
                    entry2_description_reason = 'Engulf'

                elif bullish_hammer:
                    entry2_description_reason = 'Hammer'

                elif morning_star:
                    entry2_description_reason = 'MStar'

                elif bullish_rejection:
                    entry2_description_reason = 'Reject'

                elif bullish_break_previous:
                    entry2_description_reason = 'BrkHi'

                elif bullish_strong_body:
                    entry2_description_reason = 'Strong'

                else:
                    entry2_description_reason = 'PA'

                if support_zone:
                    entry2_description_reason += ' + Support'
                    addon_zone_reason += ' + Support'

                if bullish_ob_touch:
                    entry2_description_reason += ' + OB'
                    addon_zone_reason += ' + OB'

                if bullish_fvg_touch:
                    entry2_description_reason += ' + FVG'
                    addon_zone_reason += ' + FVG'

                if self.close[0] > ema9[0] and self.close[0] > ema20[0]:
                    entry2_description_reason += ' + EMA'

                if rsi[0] > rsi[1] and rsi[0] > 40:
                    entry2_description_reason += ' + RSI'

            else:

                if bearish_breakout_volume_setup or sell_reason == 'BREAKOUT + VOLUME PULLBACK':
                    entry2_description_reason = 'Breakout Pullback'

                elif bearish_engulfing or bearish_close_momentum:
                    entry2_description_reason = 'Engulf'

                elif bearish_shooting_star:
                    entry2_description_reason = 'SStar'

                elif evening_star:
                    entry2_description_reason = 'Evening Star'

                elif bearish_rejection:
                    entry2_description_reason = 'Reject'

                elif bearish_break_previous:
                    entry2_description_reason = 'BrkLo'

                elif bearish_strong_body:
                    entry2_description_reason = 'Strong'

                else:
                    entry2_description_reason = 'PA'

                if resistance_zone:
                    entry2_description_reason += ' + Resistance'
                    addon_zone_reason += ' + Resistance'

                if bearish_ob_touch:
                    entry2_description_reason += ' + OB'
                    addon_zone_reason += ' + OB'

                if bearish_fvg_touch:
                    entry2_description_reason += ' + FVG'
                    addon_zone_reason += ' + FVG'

                if self.close[0] < ema9[0] and self.close[0] < ema20[0]:
                    entry2_description_reason += ' + EMA'

                if rsi[0] < rsi[1] and rsi[0] < 60:
                    entry2_description_reason += ' + RSI'

            entry345_description_reason = 'PA' + addon_zone_reason

            sl_text = ' | SL ' + str(round(sl[0], 2))
            tp_text = ' | TP ' + str(round(tp[0], 2))
            lot_text = ''

            if trade_lot[0] == trade_lot[0]:
                lot_text = (
                    ' | TOTAL LOT ' + str(round(trade_lot[0], 2))
                    + ' | RISK $'
                    + str(round(trade_risk_cash[0], 2))
                )

            combined_trade_description = ''

            if entry[0] == entry[0]:

                combined_trade_description += (
                    trade_symbol + ' 1 @ ' + str(round(entry[0], 2))
                    + sl_text + tp_text + lot_text
                    + ' | Reason: ' + entry1_description_reason
                )

            if second_entry_price[0] == second_entry_price[0]:

                if combined_trade_description != '':
                    combined_trade_description += '\n'

                combined_trade_description += (
                    trade_symbol + ' 2 @ '
                    + str(round(second_entry_price[0], 2))
                    + sl_text + tp_text
                    + ' | Reason: ' + entry2_description_reason
                )

            if third_entry_price[0] == third_entry_price[0]:

                if combined_trade_description != '':
                    combined_trade_description += '\n'

                combined_trade_description += (
                    trade_symbol + ' 3 @ '
                    + str(round(third_entry_price[0], 2))
                    + sl_text + tp_text
                    + ' | Reason: ' + entry345_description_reason
                )

            if fourth_entry_price[0] == fourth_entry_price[0]:

                if combined_trade_description != '':
                    combined_trade_description += '\n'

                combined_trade_description += (
                    trade_symbol + ' 4 @ '
                    + str(round(fourth_entry_price[0], 2))
                    + sl_text + tp_text
                    + ' | Reason: ' + entry345_description_reason
                )

            if fifth_entry_price[0] == fifth_entry_price[0]:

                if combined_trade_description != '':
                    combined_trade_description += '\n'

                combined_trade_description += (
                    trade_symbol + ' 5 @ '
                    + str(round(fifth_entry_price[0], 2))
                    + sl_text + tp_text
                    + ' | Reason: ' + entry345_description_reason
                )

            if self.is_closed_bar:

                pass

        # ====================================================
        # CURRENT CHART TIMEFRAME DAILY REPORT
        # CLOSED TRADES ONLY - SPREADSHEET STYLE
        # ====================================================

        if self.show_daily_report and self.is_last_bar:

            chart_minutes = self.time_frame.to_minutes()

            timeframe_label = ''

            if chart_minutes < 60:
                timeframe_label = str(chart_minutes) + ' min'
            elif chart_minutes == 60:
                timeframe_label = '1 hour'
            elif chart_minutes % 60 == 0 and chart_minutes < 1440:
                timeframe_label = str(int(chart_minutes / 60)) + ' hours'
            elif chart_minutes >= 1440 and chart_minutes % 1440 == 0:
                timeframe_label = str(int(chart_minutes / 1440)) + ' day'
            else:
                timeframe_label = str(chart_minutes) + ' min'

            sl_count = int(report_sl[0])
            tp_count = int(report_tp[0])
            trailing_sl_count = int(report_trailing_sl[0])
            active_trades = int(report_active_trades[0])
            inactive_trades = int(report_inactive_trades[0])
            total_trades = active_trades + inactive_trades
            total_exits = sl_count + tp_count + trailing_sl_count

            win_rate = 0.0
            if total_exits > 0:
                win_rate = (tp_count / total_exits) * 100.0

            report_year = int(self.report_date / 10000)
            report_month = int((self.report_date % 10000) / 100)
            report_day = int(self.report_date % 100)

            report_day_text = str(report_day)
            report_month_text = str(report_month)

            if report_day < 10:
                report_day_text = '0' + report_day_text

            if report_month < 10:
                report_month_text = '0' + report_month_text

            date_label = (
                report_day_text + '-'
                + report_month_text + '-'
                + str(report_year)
            )

            label_width = 44
            value_width = 18

            top_border = (
                '+' + ('-' * (label_width + 2))
                + '+' + ('-' * (value_width + 2)) + '+'
            )

            header_row = (
                '| ' + '𝗞𝗦 𝗧𝗥𝗔𝗗𝗘𝗥 𝗗𝗘𝗦𝗞 - 𝗗𝗔𝗜𝗟𝗬 / 𝗠𝗢𝗡𝗧𝗛𝗟𝗬 𝗣/𝗟'.ljust(label_width) + ' | '
                + 'RESULT'.ljust(value_width) + ' |'
            )

            date_row = (
                '| ' + 'Date'.ljust(label_width) + ' | '
                + date_label.ljust(value_width) + ' |'
            )

            timeframe_row = (
                '| ' + 'Time frame'.ljust(label_width) + ' | '
                + timeframe_label.ljust(value_width) + ' |'
            )

            active_row = (
                '| ' + 'Active Trades'.ljust(label_width) + ' | '
                + str(active_trades).ljust(value_width) + ' |'
            )
            inactive_row = (
                '| ' + 'Inactive Trades'.ljust(label_width) + ' | '
                + str(inactive_trades).ljust(value_width) + ' |'
            )
            total_row = (
                '| ' + 'Total trades'.ljust(label_width) + ' | '
                + str(total_trades).ljust(value_width) + ' |'
            )

            active_pnl_row = (
                '| ' + 'Active Trade P/L'.ljust(label_width) + ' | '
                + ('$' + str(round(report_active_pnl[0], 2))).ljust(value_width) + ' |'
            )
            inactive_pnl_row = (
                '| ' + 'Inactive Trade P/L'.ljust(label_width) + ' | '
                + ('$' + str(round(report_inactive_pnl[0], 2))).ljust(value_width) + ' |'
            )

            sl_row = (
                '| ' + 'StopLoss'.ljust(label_width) + ' | '
                + str(sl_count).ljust(value_width) + ' |'
            )

            tp_row = (
                '| ' + 'Target Hit'.ljust(label_width) + ' | '
                + str(tp_count).ljust(value_width) + ' |'
            )

            trailing_sl_text = (
                str(trailing_sl_count) if trailing_sl_count > 0
                else 'No trades hit'
            )
            trailing_sl_row = (
                '| ' + 'Trailing SL Hit'.ljust(label_width) + ' | '
                + trailing_sl_text.ljust(value_width) + ' |'
            )
            win_row = (
                '| ' + 'Win Rate'.ljust(label_width) + ' | '
                + (str(int(round(win_rate))) + '%').ljust(value_width) + ' |'
            )

            rr_row = (
                '| ' + 'Risk Reward'.ljust(label_width) + ' | '
                + self.risk_reward.ljust(value_width) + ' |'
            )

            risk_mode_text = 'REDUCED 3% + 1%' if reduced_risk_mode[0] == 1.0 else 'NORMAL 5% + 2%'
            risk_mode_row = (
                '| ' + 'Current Risk Mode'.ljust(label_width) + ' | '
                + risk_mode_text.ljust(value_width) + ' |'
            )

            net_profit_row = (
                '| ' + 'Daily Net P/L'.ljust(label_width) + ' | '
                + ('$' + str(round(report_net_profit[0], 2))).ljust(value_width) + ' |'
            )

            monthly_net_profit_row = (
                '| ' + 'Monthly Net P/L'.ljust(label_width) + ' | '
                + ('$' + str(round(monthly_net_profit[0], 2))).ljust(value_width) + ' |'
            )

            report_text = (
                top_border + '\n'
                + header_row + '\n'
                + top_border + '\n'
                + date_row + '\n'
                + timeframe_row + '\n'
                + active_row + '\n'
                + inactive_row + '\n'
                + total_row + '\n'
                + active_pnl_row + '\n'
                + inactive_pnl_row + '\n'
                + sl_row + '\n'
                + tp_row + '\n'
                + trailing_sl_row + '\n'
                + win_row + '\n'
                + rr_row + '\n'
                + risk_mode_row + '\n'
                + net_profit_row + '\n'
                + monthly_net_profit_row
            )

            # Optional daily breakdown for the selected month, through the current IST date.
            if self.show_monthly_daily_breakdown:
                report_text += '\n' + top_border
                report_text += '\n| ' + 'MONTHLY DAILY NET P/L'.ljust(label_width) + ' | ' + 'AMOUNT'.ljust(value_width) + ' |'
                report_text += '\n' + top_border

                days_in_selected_month = int(
                    self._selected_report_month_end_key
                    - self._selected_report_month_start_key
                )
                current_month_day_limit = int(
                    max(
                        0.0,
                        min(
                            float(days_in_selected_month),
                            current_ist_day_key - self._selected_report_month_start_key + 1.0
                        )
                    )
                )

                month_names = [
                    '', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
                ]
                selected_month_name = month_names[report_month]

                for day_number in range(1, current_month_day_limit + 1):
                    day_profit = 0.0

                    if day_number == 1:
                        day_profit = monthly_day_01_profit[0]
                    elif day_number == 2:
                        day_profit = monthly_day_02_profit[0]
                    elif day_number == 3:
                        day_profit = monthly_day_03_profit[0]
                    elif day_number == 4:
                        day_profit = monthly_day_04_profit[0]
                    elif day_number == 5:
                        day_profit = monthly_day_05_profit[0]
                    elif day_number == 6:
                        day_profit = monthly_day_06_profit[0]
                    elif day_number == 7:
                        day_profit = monthly_day_07_profit[0]
                    elif day_number == 8:
                        day_profit = monthly_day_08_profit[0]
                    elif day_number == 9:
                        day_profit = monthly_day_09_profit[0]
                    elif day_number == 10:
                        day_profit = monthly_day_10_profit[0]
                    elif day_number == 11:
                        day_profit = monthly_day_11_profit[0]
                    elif day_number == 12:
                        day_profit = monthly_day_12_profit[0]
                    elif day_number == 13:
                        day_profit = monthly_day_13_profit[0]
                    elif day_number == 14:
                        day_profit = monthly_day_14_profit[0]
                    elif day_number == 15:
                        day_profit = monthly_day_15_profit[0]
                    elif day_number == 16:
                        day_profit = monthly_day_16_profit[0]
                    elif day_number == 17:
                        day_profit = monthly_day_17_profit[0]
                    elif day_number == 18:
                        day_profit = monthly_day_18_profit[0]
                    elif day_number == 19:
                        day_profit = monthly_day_19_profit[0]
                    elif day_number == 20:
                        day_profit = monthly_day_20_profit[0]
                    elif day_number == 21:
                        day_profit = monthly_day_21_profit[0]
                    elif day_number == 22:
                        day_profit = monthly_day_22_profit[0]
                    elif day_number == 23:
                        day_profit = monthly_day_23_profit[0]
                    elif day_number == 24:
                        day_profit = monthly_day_24_profit[0]
                    elif day_number == 25:
                        day_profit = monthly_day_25_profit[0]
                    elif day_number == 26:
                        day_profit = monthly_day_26_profit[0]
                    elif day_number == 27:
                        day_profit = monthly_day_27_profit[0]
                    elif day_number == 28:
                        day_profit = monthly_day_28_profit[0]
                    elif day_number == 29:
                        day_profit = monthly_day_29_profit[0]
                    elif day_number == 30:
                        day_profit = monthly_day_30_profit[0]
                    elif day_number == 31:
                        day_profit = monthly_day_31_profit[0]

                    daily_date_text = selected_month_name + ' ' + str(day_number)
                    daily_amount_text = '$' + str(round(day_profit, 2))
                    report_text += (
                        '\n| ' + daily_date_text.ljust(label_width)
                        + ' | ' + daily_amount_text.ljust(value_width) + ' |'
                    )

                report_text += '\n' + top_border
            else:
                report_text += '\n' + top_border

            self._daily_report_label.text = report_text
            self.chart.draw(self._daily_report_label)

        # Bar number is intentionally omitted from chart drawings.

        # ====================================================
        # PRIMARY ENTRY MARKER - RESTORED FROM ORIGINAL REPO
        # ====================================================

        marker_price = nan

        if (
            buy_signal
            and not (
                self.delete_setup == 'Primary BUY'
                and self.bar_index == self.delete_bar_index
            )
        ):
            marker_price = self.low[0] - entry_marker_offset

        elif (
            sell_signal
            and not (
                self.delete_setup == 'Primary SELL'
                and self.bar_index == self.delete_bar_index
            )
        ):
            marker_price = self.high[0] + entry_marker_offset

        marker_color = (
            color.RED
            if buy_signal or sell_signal
            else color.TRANSPARENT
        )

        # ====================================================
        # VISUAL TRADE LEVELS
        # Keep the planned Entry / SL / TP visible from the setup
        # candle while the order is pending. This is display-only;
        # internal active-trade calculations continue using entry/sl/tp.
        # ====================================================

        plot_entry_value = entry[0]
        plot_sl_value = sl[0]
        plot_tp_value = tp[0]

        if side[0] != 0.0:
            plot_entry_value = midpoint_master_entry[0]
            plot_sl_value = sl[0]
            plot_tp_value = tp[0]

        # ====================================================
        # OUTPUT
        # ====================================================

        return (
            ema9[0],
            ema20[0],
            ema50[0],
            ema200[0],

            plot_entry_value,
            second_entry_price[0],
            third_entry_price[0],
            fourth_entry_price[0],
            fifth_entry_price[0],

            plot_sl_value,
            plot_tp_value,

            plot.Fill(),
            plot.Fill(),

            plot.Marker(
                value=marker_price,
                color=marker_color
            )
        )

                        self.chart.draw(LabelAbs(
                            exit_label + str(round(result_amount, 2)),
                            AbsolutePosition(self.time[0], sl[0]),
                            font_size=9, text_color=color.BLACK,
                            bg_color=color.TRANSPARENT
                        ))

                    if current_ist_day_key == risk_day_key[0]:
                        daily_realized_pnl[0] = daily_realized_pnl[0] + realized_pnl
                        daily_loss_threshold = daily_start_balance[0] * 0.30
                        if daily_realized_pnl[0] <= -daily_loss_threshold:
                            reduced_risk_mode[0] = 1.0
                        elif daily_realized_pnl[0] >= 0.0:
                            reduced_risk_mode[0] = 0.0

                    if current_ist_day_key == self._selected_report_day_key:
                        if report_hit_trailing_sl:
                            report_trailing_sl[0] = report_trailing_sl[0] + 1.0
                        elif report_hit_sl:
                            report_sl[0] = report_sl[0] + 1.0
                        elif report_hit_tp:
                            report_tp[0] = report_tp[0] + 1.0
                        report_net_profit[0] = report_net_profit[0] + realized_pnl
                        report_active_pnl[0] = report_active_pnl[0] + realized_pnl

                    if (
                        current_ist_day_key >= self._selected_report_month_start_key
                        and current_ist_day_key < self._selected_report_month_end_key
                    ):
                        monthly_net_profit[0] = monthly_net_profit[0] + realized_pnl
                    if current_ist_day_key == self._selected_report_month_start_key + 0.0:
                        monthly_day_01_profit[0] = monthly_day_01_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 1.0:
                        monthly_day_02_profit[0] = monthly_day_02_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 2.0:
                        monthly_day_03_profit[0] = monthly_day_03_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 3.0:
                        monthly_day_04_profit[0] = monthly_day_04_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 4.0:
                        monthly_day_05_profit[0] = monthly_day_05_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 5.0:
                        monthly_day_06_profit[0] = monthly_day_06_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 6.0:
                        monthly_day_07_profit[0] = monthly_day_07_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 7.0:
                        monthly_day_08_profit[0] = monthly_day_08_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 8.0:
                        monthly_day_09_profit[0] = monthly_day_09_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 9.0:
                        monthly_day_10_profit[0] = monthly_day_10_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 10.0:
                        monthly_day_11_profit[0] = monthly_day_11_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 11.0:
                        monthly_day_12_profit[0] = monthly_day_12_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 12.0:
                        monthly_day_13_profit[0] = monthly_day_13_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 13.0:
                        monthly_day_14_profit[0] = monthly_day_14_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 14.0:
                        monthly_day_15_profit[0] = monthly_day_15_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 15.0:
                        monthly_day_16_profit[0] = monthly_day_16_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 16.0:
                        monthly_day_17_profit[0] = monthly_day_17_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 17.0:
                        monthly_day_18_profit[0] = monthly_day_18_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 18.0:
                        monthly_day_19_profit[0] = monthly_day_19_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 19.0:
                        monthly_day_20_profit[0] = monthly_day_20_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 20.0:
                        monthly_day_21_profit[0] = monthly_day_21_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 21.0:
                        monthly_day_22_profit[0] = monthly_day_22_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 22.0:
                        monthly_day_23_profit[0] = monthly_day_23_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 23.0:
                        monthly_day_24_profit[0] = monthly_day_24_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 24.0:
                        monthly_day_25_profit[0] = monthly_day_25_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 25.0:
                        monthly_day_26_profit[0] = monthly_day_26_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 26.0:
                        monthly_day_27_profit[0] = monthly_day_27_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 27.0:
                        monthly_day_28_profit[0] = monthly_day_28_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 28.0:
                        monthly_day_29_profit[0] = monthly_day_29_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 29.0:
                        monthly_day_30_profit[0] = monthly_day_30_profit[0] + realized_pnl
                    elif current_ist_day_key == self._selected_report_month_start_key + 30.0:
                        monthly_day_31_profit[0] = monthly_day_31_profit[0] + realized_pnl

                entry[0] = nan
                early_leg_entry[0] = nan
                midpoint_master_entry[0] = nan
                early_leg_lot[0] = nan
                mid_leg_lot[0] = nan
                mid_leg_active[0] = 0.0
                early_leg_closed[0] = 0.0
                pending_mid_entry[0] = nan
                pending_early_entry[0] = nan
                pending_trade_side[0] = 0.0
                pending_trade_entry[0] = nan
                pending_trade_sl[0] = nan
                pending_trade_tp[0] = nan
                pending_trade_lot[0] = nan
                pending_trade_risk_cash[0] = nan
                pending_trade_setup_day[0] = nan
                pending_trade_setup_bar[0] = -1.0
                second_entry_price[0] = nan
                third_entry_price[0] = nan
                fourth_entry_price[0] = nan
                fifth_entry_price[0] = nan
                sl[0] = nan
                tp[0] = nan
                side[0] = 0.0
                trade_lot[0] = nan
                trade_risk_cash[0] = nan
                original_risk_distance[0] = nan
                favorable_extreme[0] = nan
                trail_candidate[0] = nan
                trail_confirm_count[0] = 0.0
                trail_stage[0] = 0.0
                trail_last_update_bar[0] = -1.0
                entry_count[0] = 0.0
                last_entry_bar[0] = -1.0
                last_entry_price[0] = nan
                entry_label_time[0] = nan
                early_exit_warned[0] = 0.0
                pending_buy[0] = 0.0
                pending_buy_average[0] = nan
                pending_buy_low[0] = nan
                pending_buy_bar[0] = -1.0
                pending_sell[0] = 0.0
                pending_sell_average[0] = nan
                pending_sell_high[0] = nan
                pending_sell_bar[0] = -1.0
                trade_exited = True

            # ================================================
            # ADAPTIVE HYBRID TRAILING (M1, CLOSED CANDLES ONLY)
            # ================================================
            # This is a chart-side simulated stop line. Exness Indie custom
            # indicators cannot modify an actual broker position's SL.
            if (
                self.adaptive_trailing_enabled
                and self._is_m1_chart
                and side[0] != 0.0
                and mid_leg_active[0] == 1.0
                and self.bar_index > last_entry_bar[0]
                and original_risk_distance[0] > 0.0
                and not trade_exited
            ):
                is_buy_trail = side[0] == 1.0
                entry[0] = midpoint_master_entry[0]
                risk_unit = original_risk_distance[0]
                atr_value = atr14[0]
                adx_value = adx14[0]
                minus_value = minus_di[0]
                plus_value = plus_di[0]
                proposed_sl = sl[0]

                # Track the best favourable excursion since the simulated entry.
                # Declare shared-scope values before the BUY/SELL branches.
                favourable_move = 0.0
                target_distance = 0.0
                if is_buy_trail:
                    if isnan(favorable_extreme[0]):
                        favorable_extreme[0] = self.high[0]
                    else:
                        favorable_extreme[0] = max(favorable_extreme[0], self.high[0])
                    favourable_move = favorable_extreme[0] - entry[0]
                    target_distance = tp[0] - entry[0]
                else:
                    if isnan(favorable_extreme[0]):
                        favorable_extreme[0] = self.low[0]
                    else:
                        favorable_extreme[0] = min(favorable_extreme[0], self.low[0])
                    favourable_move = entry[0] - favorable_extreme[0]
                    target_distance = entry[0] - tp[0]

                r_progress = favourable_move / risk_unit if risk_unit > 0.0 else 0.0
                tp_progress = (
                    favourable_move / target_distance
                    if target_distance > 0.0 else 0.0
                )

                # 1R: break-even (optional user-supplied cost buffer).
                if r_progress >= 1.0:
                    if is_buy_trail:
                        proposed_sl = max(proposed_sl, entry[0] + self.break_even_buffer)
                    else:
                        proposed_sl = min(proposed_sl, entry[0] - self.break_even_buffer)

                # TP progress locks are based on the ORIGINAL risk distance.
                if tp_progress >= 0.95:
                    lock_price = 0.60 * risk_unit
                    if is_buy_trail:
                        proposed_sl = max(proposed_sl, entry[0] + lock_price)
                    else:
                        proposed_sl = min(proposed_sl, entry[0] - lock_price)
                elif tp_progress >= 0.85:
                    lock_price = 0.30 * risk_unit
                    if is_buy_trail:
                        proposed_sl = max(proposed_sl, entry[0] + lock_price)
                    else:
                        proposed_sl = min(proposed_sl, entry[0] - lock_price)

                # Swing structure + ATR trailing begins after 1.4R.
                if r_progress >= 1.4 and not isnan(atr_value) and atr_value > 0.0:
                    strong_buy_trend = (
                        adx_value >= 25.0
                        and plus_value > minus_value
                        and trail_ema9[0] > trail_ema21[0]
                    )
                    strong_sell_trend = (
                        adx_value >= 25.0
                        and minus_value > plus_value
                        and trail_ema9[0] < trail_ema21[0]
                    )
                    atr_multiplier = 1.5 if (
                        (is_buy_trail and strong_buy_trend)
                        or ((not is_buy_trail) and strong_sell_trend)
                    ) else 1.0
                    atr_buffer = atr_value * atr_multiplier

                    if is_buy_trail:
                        # Confirmed pivot low: two bars on either side.
                        confirmed_swing_low = (
                            self.low[2] < self.low[1]
                            and self.low[2] < self.low[0]
                            and self.low[2] <= self.low[3]
                            and self.low[2] <= self.low[4]
                        )
                        if confirmed_swing_low:
                            swing_candidate = self.low[2] - atr_buffer
                            if swing_candidate > proposed_sl and swing_candidate < self.close[0]:
                                proposed_sl = max(proposed_sl, swing_candidate)

                        # Three bearish closes are a confirmed adverse reaction.
                        bearish_three = (
                            self.close[0] < self.close[1]
                            and self.close[1] < self.close[2]
                            and self.close[0] < trail_ema9[0]
                        )
                        if bearish_three:
                            reaction_candidate = min([
                                self.low[0], self.low[1], self.low[2]
                            ]) - atr_value
                            if reaction_candidate > proposed_sl and reaction_candidate < self.close[0]:
                                proposed_sl = max(proposed_sl, reaction_candidate)
                    else:
                        # Confirmed pivot high: two bars on either side.
                        confirmed_swing_high = (
                            self.high[2] > self.high[1]
                            and self.high[2] > self.high[0]
                            and self.high[2] >= self.high[3]
                            and self.high[2] >= self.high[4]
                        )
                        if confirmed_swing_high:
                            swing_candidate = self.high[2] + atr_buffer
                            if swing_candidate < proposed_sl and swing_candidate > self.close[0]:
                                proposed_sl = min(proposed_sl, swing_candidate)

                        # Three bullish closes are a confirmed adverse reaction.
                        bullish_three = (
                            self.close[0] > self.close[1]
                            and self.close[1] > self.close[2]
                            and self.close[0] > trail_ema9[0]
                        )
                        if bullish_three:
                            reaction_candidate = max([
                                self.high[0], self.high[1], self.high[2]
                            ]) + atr_value
                            if reaction_candidate < proposed_sl and reaction_candidate > self.close[0]:
                                proposed_sl = min(proposed_sl, reaction_candidate)

                # Candidate must improve protection and remain beyond the close.
                candidate_is_valid = (
                    proposed_sl > sl[0] and proposed_sl < self.close[0]
                    if is_buy_trail else
                    proposed_sl < sl[0] and proposed_sl > self.close[0]
                )

                # Require 3 consecutive completed M1 closes to confirm the same
                # or a more protective candidate. Never loosen an existing stop.
                if candidate_is_valid:
                    if is_buy_trail:
                        if isnan(trail_candidate[0]) or proposed_sl > trail_candidate[0]:
                            trail_candidate[0] = proposed_sl
                            trail_confirm_count[0] = 0.0
                    else:
                        if isnan(trail_candidate[0]) or proposed_sl < trail_candidate[0]:
                            trail_candidate[0] = proposed_sl
                            trail_confirm_count[0] = 0.0

                if not isnan(trail_candidate[0]):
                    candidate_still_safe = (
                        self.close[0] > trail_candidate[0]
                        if is_buy_trail else
                        self.close[0] < trail_candidate[0]
                    )
                    if candidate_still_safe:
                        trail_confirm_count[0] = trail_confirm_count[0] + 1.0
                    else:
                        trail_candidate[0] = nan
                        trail_confirm_count[0] = 0.0

                if (
                    not isnan(trail_candidate[0])
                    and trail_confirm_count[0] >= 3.0
                    and (
                        (is_buy_trail and trail_candidate[0] > sl[0])
                        or ((not is_buy_trail) and trail_candidate[0] < sl[0])
                    )
                ):
                    sl[0] = trail_candidate[0]
                    trail_last_update_bar[0] = float(self.bar_index)
                    trail_confirm_count[0] = 0.0
                    trail_candidate[0] = nan

                    # Draw each label inside its own branch. Indie variables
                    # declared inside an indented branch are not visible outside it.
                    if tp_progress >= 0.95:
                        trail_stage[0] = 3.0
                        self.chart.draw(
                            LabelAbs(
                                'ADAPTIVE SL: LOCK 0.60R',
                                AbsolutePosition(self.time[0], sl[0]),
                                font_size=9,
                                text_color=color.BLACK,
                                bg_color=color.TRANSPARENT
                            )
                        )
                    elif tp_progress >= 0.85:
                        trail_stage[0] = 2.0
                        self.chart.draw(
                            LabelAbs(
                                'ADAPTIVE SL: LOCK 0.30R',
                                AbsolutePosition(self.time[0], sl[0]),
                                font_size=9,
                                text_color=color.BLACK,
                                bg_color=color.TRANSPARENT
                            )
                        )
                    elif r_progress >= 1.0:
                        trail_stage[0] = 1.0
                        self.chart.draw(
                            LabelAbs(
                                'ADAPTIVE SL: BREAK EVEN / TRAIL',
                                AbsolutePosition(self.time[0], sl[0]),
                                font_size=9,
                                text_color=color.BLACK,
                                bg_color=color.TRANSPARENT
                            )
                        )
                    else:
                        trail_stage[0] = 4.0
                        self.chart.draw(
                            LabelAbs(
                                'ADAPTIVE SL: STRUCTURE TRAIL',
                                AbsolutePosition(self.time[0], sl[0]),
                                font_size=9,
                                text_color=color.BLACK,
                                bg_color=color.TRANSPARENT
                            )
                        )

                entry[0] = early_leg_entry[0]

            # ================================================
            # EARLY EXIT WARNING
            # ================================================

            if side[0] == 1.0 and early_exit_warned[0] == 0.0:

                buy_failure_score = 0

                if self.close[0] < ema20[0] and ema20[0] < ema50[0]:
                    buy_failure_score += 1

                if htf_sell:
                    buy_failure_score += 1

                if rsi[0] < 45 and rsi[0] < rsi[1]:
                    buy_failure_score += 1

                if bearish_price_action:
                    buy_failure_score += 1

                if buy_failure_score >= 3:

                    early_exit_warned[0] = 1.0

                    if self.is_closed_bar:

                        pass

            elif side[0] == -1.0 and early_exit_warned[0] == 0.0:

                sell_failure_score = 0

                if self.close[0] > ema20[0] and ema20[0] > ema50[0]:
                    sell_failure_score += 1

                if htf_buy:
                    sell_failure_score += 1

                if rsi[0] > 55 and rsi[0] > rsi[1]:
                    sell_failure_score += 1

                if bullish_price_action:
                    sell_failure_score += 1

                if sell_failure_score >= 3:

                    early_exit_warned[0] = 1.0

                    if self.is_closed_bar:

                        pass

            # ================================================
            # ADD-ON ENTRIES 2 TO 5
            # ================================================

            if (
                side[0] != 0.0
                and entry_count[0] >= 1.0
                and entry_count[0] < 5.0
                and self.bar_index > last_entry_bar[0]
            ):

                is_buy_side = side[0] == 1.0

                add_ok = False

                if is_buy_side:

                    add_ok = (
                        candidate_entry_price < last_entry_price[0]
                        and bullish_price_action
                        and buy_add_location
                        and buy_add_score >= 4
                    )

                else:

                    add_ok = (
                        candidate_entry_price > last_entry_price[0]
                        and bearish_price_action
                        and sell_add_location
                        and sell_add_score >= 4
                    )

                if add_ok:

                    new_count = entry_count[0] + 1.0

                    entry_count[0] = new_count
                    last_entry_bar[0] = float(self.bar_index)
                    last_entry_price[0] = candidate_entry_price

                    add_name = 'Second'
                    add_color = color.BLACK

                    if new_count == 2.0:
                        second_entry_price[0] = candidate_entry_price

                    elif new_count == 3.0:
                        third_entry_price[0] = candidate_entry_price
                        add_name = 'Third'
                        add_color = color.FUCHSIA

                    elif new_count == 4.0:
                        fourth_entry_price[0] = candidate_entry_price
                        add_name = 'Fourth'
                        add_color = color.YELLOW

                    else:
                        fifth_entry_price[0] = candidate_entry_price
                        add_name = 'Fifth'
                        add_color = color.PURPLE

                    add_setup_name = add_name + (
                        ' BUY' if is_buy_side else ' SELL'
                    )

                    if not (
                        self.delete_setup == add_setup_name
                        and self.bar_index == self.delete_bar_index
                    ):

                        if is_buy_side:

                            if self.is_closed_bar:

                                pass

                        else:

                            if self.is_closed_bar:

                                pass

            # ================================================
            # ARM NEW BREAKOUT PULLBACK SETUPS
            # ================================================

            if side[0] == 0.0 and not trade_exited:

                if bullish_breakout_volume_setup:

                    pending_buy[0] = 1.0
                    pending_buy_average[0] = (
                        self.high[0] + self.low[0]
                    ) / 2.0
                    pending_buy_low[0] = self.low[0]
                    pending_buy_bar[0] = float(self.bar_index)

                    pending_sell[0] = 0.0
                    pending_sell_average[0] = nan
                    pending_sell_high[0] = nan
                    pending_sell_bar[0] = -1.0

                elif bearish_breakout_volume_setup:

                    pending_sell[0] = 1.0
                    pending_sell_average[0] = (
                        self.high[0] + self.low[0]
                    ) / 2.0
                    pending_sell_high[0] = self.high[0]
                    pending_sell_bar[0] = float(self.bar_index)

                    pending_buy[0] = 0.0
                    pending_buy_average[0] = nan
                    pending_buy_low[0] = nan
                    pending_buy_bar[0] = -1.0

            # ================================================
            # VALIDATE / EXPIRE PENDING BUY SETUP
            # ================================================

            if (
                pending_buy[0] == 1.0
                and self.bar_index > pending_buy_bar[0]
            ):

                buy_pending_age = (
                    self.bar_index - pending_buy_bar[0]
                )

                if (
                    buy_pending_age > 10.0
                    or self.close[0] < pending_buy_low[0]
                ):

                    pending_buy[0] = 0.0
                    pending_buy_average[0] = nan
                    pending_buy_low[0] = nan
                    pending_buy_bar[0] = -1.0

            # ================================================
            # VALIDATE / EXPIRE PENDING SELL SETUP
            # ================================================

            if (
                pending_sell[0] == 1.0
                and self.bar_index > pending_sell_bar[0]
            ):

                sell_pending_age = (
                    self.bar_index - pending_sell_bar[0]
                )

                if (
                    sell_pending_age > 10.0
                    or self.close[0] > pending_sell_high[0]
                ):

                    pending_sell[0] = 0.0
                    pending_sell_average[0] = nan
                    pending_sell_high[0] = nan
                    pending_sell_bar[0] = -1.0

            # ================================================
            # CHECK BUY PULLBACK ENTRY
            # ================================================

            buy_breakout_pullback_ready = False
            buy_breakout_entry_price = nan

            bullish_pullback_confirmation = (
                self.close[0] > self.open[0]
                and (
                    bullish_rejection
                    or bullish_engulfing
                    or bullish_hammer
                    or bullish_close_momentum
                )
            )

            if (
                pending_buy[0] == 1.0
                and self.bar_index > pending_buy_bar[0]
                and bullish_pullback_confirmation
            ):

                buy_average_touched = (
                    self.low[0] <= pending_buy_average[0]
                    and self.close[0] > pending_buy_average[0]
                )

                buy_bottom_touched = (
                    self.low[0] <= pending_buy_low[0]
                    and self.close[0] > pending_buy_low[0]
                )

                if buy_average_touched:

                    buy_breakout_pullback_ready = True
                    buy_breakout_entry_price = pending_buy_average[0]

                elif buy_bottom_touched:

                    buy_breakout_pullback_ready = True
                    buy_breakout_entry_price = pending_buy_low[0]

            # ================================================
            # CHECK SELL PULLBACK ENTRY
            # ================================================

            sell_breakout_pullback_ready = False
            sell_breakout_entry_price = nan

            bearish_pullback_confirmation = (
                self.close[0] < self.open[0]
                and (
                    bearish_rejection
                    or bearish_engulfing
                    or bearish_shooting_star
                    or bearish_close_momentum
                )
            )

            if (
                pending_sell[0] == 1.0
                and self.bar_index > pending_sell_bar[0]
                and bearish_pullback_confirmation
            ):

                sell_average_touched = (
                    self.high[0] >= pending_sell_average[0]
                    and self.close[0] < pending_sell_average[0]
                )

                sell_top_touched = (
                    self.high[0] >= pending_sell_high[0]
                    and self.close[0] < pending_sell_high[0]
                )

                if sell_average_touched:

                    sell_breakout_pullback_ready = True
                    sell_breakout_entry_price = pending_sell_average[0]

                elif sell_top_touched:

                    sell_breakout_pullback_ready = True
                    sell_breakout_entry_price = pending_sell_high[0]

            # ================================================
            # DYNAMIC DAILY RISK BUDGET
            # ================================================

            if reduced_risk_mode[0] == 1.0:
                total_risk_percent = reduced_risk_percent
            else:
                total_risk_percent = normal_risk_percent

            risk_budget_cash = (
                self.account_capital * total_risk_percent / 100.0
            )

            # Independent original-midpoint setup counter.
            # Resolve every outstanding setup independently before arming this bar's setup.
            # SL/TP wins over midpoint if both are touched on the same candle.
            if self.is_closed_bar:
                if count_1_side[0] != 0.0 and self.bar_index > count_1_bar[0]:
                    count_1_entry_touched = (
                        self.low[0] <= count_1_entry[0]
                        if count_1_side[0] == 1.0 else
                        self.high[0] >= count_1_entry[0]
                    )
                    count_1_sl_touched = (
                        self.low[0] <= count_1_sl[0]
                        if count_1_side[0] == 1.0 else
                        self.high[0] >= count_1_sl[0]
                    )
                    count_1_tp_touched = (
                        self.high[0] >= count_1_tp[0]
                        if count_1_side[0] == 1.0 else
                        self.low[0] <= count_1_tp[0]
                    )
                    if count_1_sl_touched or count_1_tp_touched:
                        if count_1_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_1_side[0] = 0.0
                        count_1_entry[0] = nan
                        count_1_sl[0] = nan
                        count_1_tp[0] = nan
                        count_1_day[0] = nan
                        count_1_bar[0] = -1.0
                    elif count_1_entry_touched:
                        if count_1_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_1_side[0] = 0.0
                        count_1_entry[0] = nan
                        count_1_sl[0] = nan
                        count_1_tp[0] = nan
                        count_1_day[0] = nan
                        count_1_bar[0] = -1.0

                if count_2_side[0] != 0.0 and self.bar_index > count_2_bar[0]:
                    count_2_entry_touched = (
                        self.low[0] <= count_2_entry[0]
                        if count_2_side[0] == 1.0 else
                        self.high[0] >= count_2_entry[0]
                    )
                    count_2_sl_touched = (
                        self.low[0] <= count_2_sl[0]
                        if count_2_side[0] == 1.0 else
                        self.high[0] >= count_2_sl[0]
                    )
                    count_2_tp_touched = (
                        self.high[0] >= count_2_tp[0]
                        if count_2_side[0] == 1.0 else
                        self.low[0] <= count_2_tp[0]
                    )
                    if count_2_sl_touched or count_2_tp_touched:
                        if count_2_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_2_side[0] = 0.0
                        count_2_entry[0] = nan
                        count_2_sl[0] = nan
                        count_2_tp[0] = nan
                        count_2_day[0] = nan
                        count_2_bar[0] = -1.0
                    elif count_2_entry_touched:
                        if count_2_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_2_side[0] = 0.0
                        count_2_entry[0] = nan
                        count_2_sl[0] = nan
                        count_2_tp[0] = nan
                        count_2_day[0] = nan
                        count_2_bar[0] = -1.0

                if count_3_side[0] != 0.0 and self.bar_index > count_3_bar[0]:
                    count_3_entry_touched = (
                        self.low[0] <= count_3_entry[0]
                        if count_3_side[0] == 1.0 else
                        self.high[0] >= count_3_entry[0]
                    )
                    count_3_sl_touched = (
                        self.low[0] <= count_3_sl[0]
                        if count_3_side[0] == 1.0 else
                        self.high[0] >= count_3_sl[0]
                    )
                    count_3_tp_touched = (
                        self.high[0] >= count_3_tp[0]
                        if count_3_side[0] == 1.0 else
                        self.low[0] <= count_3_tp[0]
                    )
                    if count_3_sl_touched or count_3_tp_touched:
                        if count_3_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_3_side[0] = 0.0
                        count_3_entry[0] = nan
                        count_3_sl[0] = nan
                        count_3_tp[0] = nan
                        count_3_day[0] = nan
                        count_3_bar[0] = -1.0
                    elif count_3_entry_touched:
                        if count_3_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_3_side[0] = 0.0
                        count_3_entry[0] = nan
                        count_3_sl[0] = nan
                        count_3_tp[0] = nan
                        count_3_day[0] = nan
                        count_3_bar[0] = -1.0

                if count_4_side[0] != 0.0 and self.bar_index > count_4_bar[0]:
                    count_4_entry_touched = (
                        self.low[0] <= count_4_entry[0]
                        if count_4_side[0] == 1.0 else
                        self.high[0] >= count_4_entry[0]
                    )
                    count_4_sl_touched = (
                        self.low[0] <= count_4_sl[0]
                        if count_4_side[0] == 1.0 else
                        self.high[0] >= count_4_sl[0]
                    )
                    count_4_tp_touched = (
                        self.high[0] >= count_4_tp[0]
                        if count_4_side[0] == 1.0 else
                        self.low[0] <= count_4_tp[0]
                    )
                    if count_4_sl_touched or count_4_tp_touched:
                        if count_4_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_4_side[0] = 0.0
                        count_4_entry[0] = nan
                        count_4_sl[0] = nan
                        count_4_tp[0] = nan
                        count_4_day[0] = nan
                        count_4_bar[0] = -1.0
                    elif count_4_entry_touched:
                        if count_4_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_4_side[0] = 0.0
                        count_4_entry[0] = nan
                        count_4_sl[0] = nan
                        count_4_tp[0] = nan
                        count_4_day[0] = nan
                        count_4_bar[0] = -1.0

                if count_5_side[0] != 0.0 and self.bar_index > count_5_bar[0]:
                    count_5_entry_touched = (
                        self.low[0] <= count_5_entry[0]
                        if count_5_side[0] == 1.0 else
                        self.high[0] >= count_5_entry[0]
                    )
                    count_5_sl_touched = (
                        self.low[0] <= count_5_sl[0]
                        if count_5_side[0] == 1.0 else
                        self.high[0] >= count_5_sl[0]
                    )
                    count_5_tp_touched = (
                        self.high[0] >= count_5_tp[0]
                        if count_5_side[0] == 1.0 else
                        self.low[0] <= count_5_tp[0]
                    )
                    if count_5_sl_touched or count_5_tp_touched:
                        if count_5_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_5_side[0] = 0.0
                        count_5_entry[0] = nan
                        count_5_sl[0] = nan
                        count_5_tp[0] = nan
                        count_5_day[0] = nan
                        count_5_bar[0] = -1.0
                    elif count_5_entry_touched:
                        if count_5_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_5_side[0] = 0.0
                        count_5_entry[0] = nan
                        count_5_sl[0] = nan
                        count_5_tp[0] = nan
                        count_5_day[0] = nan
                        count_5_bar[0] = -1.0

                if count_6_side[0] != 0.0 and self.bar_index > count_6_bar[0]:
                    count_6_entry_touched = (
                        self.low[0] <= count_6_entry[0]
                        if count_6_side[0] == 1.0 else
                        self.high[0] >= count_6_entry[0]
                    )
                    count_6_sl_touched = (
                        self.low[0] <= count_6_sl[0]
                        if count_6_side[0] == 1.0 else
                        self.high[0] >= count_6_sl[0]
                    )
                    count_6_tp_touched = (
                        self.high[0] >= count_6_tp[0]
                        if count_6_side[0] == 1.0 else
                        self.low[0] <= count_6_tp[0]
                    )
                    if count_6_sl_touched or count_6_tp_touched:
                        if count_6_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_6_side[0] = 0.0
                        count_6_entry[0] = nan
                        count_6_sl[0] = nan
                        count_6_tp[0] = nan
                        count_6_day[0] = nan
                        count_6_bar[0] = -1.0
                    elif count_6_entry_touched:
                        if count_6_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_6_side[0] = 0.0
                        count_6_entry[0] = nan
                        count_6_sl[0] = nan
                        count_6_tp[0] = nan
                        count_6_day[0] = nan
                        count_6_bar[0] = -1.0

                if count_7_side[0] != 0.0 and self.bar_index > count_7_bar[0]:
                    count_7_entry_touched = (
                        self.low[0] <= count_7_entry[0]
                        if count_7_side[0] == 1.0 else
                        self.high[0] >= count_7_entry[0]
                    )
                    count_7_sl_touched = (
                        self.low[0] <= count_7_sl[0]
                        if count_7_side[0] == 1.0 else
                        self.high[0] >= count_7_sl[0]
                    )
                    count_7_tp_touched = (
                        self.high[0] >= count_7_tp[0]
                        if count_7_side[0] == 1.0 else
                        self.low[0] <= count_7_tp[0]
                    )
                    if count_7_sl_touched or count_7_tp_touched:
                        if count_7_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_7_side[0] = 0.0
                        count_7_entry[0] = nan
                        count_7_sl[0] = nan
                        count_7_tp[0] = nan
                        count_7_day[0] = nan
                        count_7_bar[0] = -1.0
                    elif count_7_entry_touched:
                        if count_7_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_7_side[0] = 0.0
                        count_7_entry[0] = nan
                        count_7_sl[0] = nan
                        count_7_tp[0] = nan
                        count_7_day[0] = nan
                        count_7_bar[0] = -1.0

                if count_8_side[0] != 0.0 and self.bar_index > count_8_bar[0]:
                    count_8_entry_touched = (
                        self.low[0] <= count_8_entry[0]
                        if count_8_side[0] == 1.0 else
                        self.high[0] >= count_8_entry[0]
                    )
                    count_8_sl_touched = (
                        self.low[0] <= count_8_sl[0]
                        if count_8_side[0] == 1.0 else
                        self.high[0] >= count_8_sl[0]
                    )
                    count_8_tp_touched = (
                        self.high[0] >= count_8_tp[0]
                        if count_8_side[0] == 1.0 else
                        self.low[0] <= count_8_tp[0]
                    )
                    if count_8_sl_touched or count_8_tp_touched:
                        if count_8_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_8_side[0] = 0.0
                        count_8_entry[0] = nan
                        count_8_sl[0] = nan
                        count_8_tp[0] = nan
                        count_8_day[0] = nan
                        count_8_bar[0] = -1.0
                    elif count_8_entry_touched:
                        if count_8_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_8_side[0] = 0.0
                        count_8_entry[0] = nan
                        count_8_sl[0] = nan
                        count_8_tp[0] = nan
                        count_8_day[0] = nan
                        count_8_bar[0] = -1.0

                if count_9_side[0] != 0.0 and self.bar_index > count_9_bar[0]:
                    count_9_entry_touched = (
                        self.low[0] <= count_9_entry[0]
                        if count_9_side[0] == 1.0 else
                        self.high[0] >= count_9_entry[0]
                    )
                    count_9_sl_touched = (
                        self.low[0] <= count_9_sl[0]
                        if count_9_side[0] == 1.0 else
                        self.high[0] >= count_9_sl[0]
                    )
                    count_9_tp_touched = (
                        self.high[0] >= count_9_tp[0]
                        if count_9_side[0] == 1.0 else
                        self.low[0] <= count_9_tp[0]
                    )
                    if count_9_sl_touched or count_9_tp_touched:
                        if count_9_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_9_side[0] = 0.0
                        count_9_entry[0] = nan
                        count_9_sl[0] = nan
                        count_9_tp[0] = nan
                        count_9_day[0] = nan
                        count_9_bar[0] = -1.0
                    elif count_9_entry_touched:
                        if count_9_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_9_side[0] = 0.0
                        count_9_entry[0] = nan
                        count_9_sl[0] = nan
                        count_9_tp[0] = nan
                        count_9_day[0] = nan
                        count_9_bar[0] = -1.0

                if count_10_side[0] != 0.0 and self.bar_index > count_10_bar[0]:
                    count_10_entry_touched = (
                        self.low[0] <= count_10_entry[0]
                        if count_10_side[0] == 1.0 else
                        self.high[0] >= count_10_entry[0]
                    )
                    count_10_sl_touched = (
                        self.low[0] <= count_10_sl[0]
                        if count_10_side[0] == 1.0 else
                        self.high[0] >= count_10_sl[0]
                    )
                    count_10_tp_touched = (
                        self.high[0] >= count_10_tp[0]
                        if count_10_side[0] == 1.0 else
                        self.low[0] <= count_10_tp[0]
                    )
                    if count_10_sl_touched or count_10_tp_touched:
                        if count_10_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_10_side[0] = 0.0
                        count_10_entry[0] = nan
                        count_10_sl[0] = nan
                        count_10_tp[0] = nan
                        count_10_day[0] = nan
                        count_10_bar[0] = -1.0
                    elif count_10_entry_touched:
                        if count_10_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_10_side[0] = 0.0
                        count_10_entry[0] = nan
                        count_10_sl[0] = nan
                        count_10_tp[0] = nan
                        count_10_day[0] = nan
                        count_10_bar[0] = -1.0

                if count_11_side[0] != 0.0 and self.bar_index > count_11_bar[0]:
                    count_11_entry_touched = (
                        self.low[0] <= count_11_entry[0]
                        if count_11_side[0] == 1.0 else
                        self.high[0] >= count_11_entry[0]
                    )
                    count_11_sl_touched = (
                        self.low[0] <= count_11_sl[0]
                        if count_11_side[0] == 1.0 else
                        self.high[0] >= count_11_sl[0]
                    )
                    count_11_tp_touched = (
                        self.high[0] >= count_11_tp[0]
                        if count_11_side[0] == 1.0 else
                        self.low[0] <= count_11_tp[0]
                    )
                    if count_11_sl_touched or count_11_tp_touched:
                        if count_11_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_11_side[0] = 0.0
                        count_11_entry[0] = nan
                        count_11_sl[0] = nan
                        count_11_tp[0] = nan
                        count_11_day[0] = nan
                        count_11_bar[0] = -1.0
                    elif count_11_entry_touched:
                        if count_11_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_11_side[0] = 0.0
                        count_11_entry[0] = nan
                        count_11_sl[0] = nan
                        count_11_tp[0] = nan
                        count_11_day[0] = nan
                        count_11_bar[0] = -1.0

                if count_12_side[0] != 0.0 and self.bar_index > count_12_bar[0]:
                    count_12_entry_touched = (
                        self.low[0] <= count_12_entry[0]
                        if count_12_side[0] == 1.0 else
                        self.high[0] >= count_12_entry[0]
                    )
                    count_12_sl_touched = (
                        self.low[0] <= count_12_sl[0]
                        if count_12_side[0] == 1.0 else
                        self.high[0] >= count_12_sl[0]
                    )
                    count_12_tp_touched = (
                        self.high[0] >= count_12_tp[0]
                        if count_12_side[0] == 1.0 else
                        self.low[0] <= count_12_tp[0]
                    )
                    if count_12_sl_touched or count_12_tp_touched:
                        if count_12_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_12_side[0] = 0.0
                        count_12_entry[0] = nan
                        count_12_sl[0] = nan
                        count_12_tp[0] = nan
                        count_12_day[0] = nan
                        count_12_bar[0] = -1.0
                    elif count_12_entry_touched:
                        if count_12_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_12_side[0] = 0.0
                        count_12_entry[0] = nan
                        count_12_sl[0] = nan
                        count_12_tp[0] = nan
                        count_12_day[0] = nan
                        count_12_bar[0] = -1.0

                if count_13_side[0] != 0.0 and self.bar_index > count_13_bar[0]:
                    count_13_entry_touched = (
                        self.low[0] <= count_13_entry[0]
                        if count_13_side[0] == 1.0 else
                        self.high[0] >= count_13_entry[0]
                    )
                    count_13_sl_touched = (
                        self.low[0] <= count_13_sl[0]
                        if count_13_side[0] == 1.0 else
                        self.high[0] >= count_13_sl[0]
                    )
                    count_13_tp_touched = (
                        self.high[0] >= count_13_tp[0]
                        if count_13_side[0] == 1.0 else
                        self.low[0] <= count_13_tp[0]
                    )
                    if count_13_sl_touched or count_13_tp_touched:
                        if count_13_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_13_side[0] = 0.0
                        count_13_entry[0] = nan
                        count_13_sl[0] = nan
                        count_13_tp[0] = nan
                        count_13_day[0] = nan
                        count_13_bar[0] = -1.0
                    elif count_13_entry_touched:
                        if count_13_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_13_side[0] = 0.0
                        count_13_entry[0] = nan
                        count_13_sl[0] = nan
                        count_13_tp[0] = nan
                        count_13_day[0] = nan
                        count_13_bar[0] = -1.0

                if count_14_side[0] != 0.0 and self.bar_index > count_14_bar[0]:
                    count_14_entry_touched = (
                        self.low[0] <= count_14_entry[0]
                        if count_14_side[0] == 1.0 else
                        self.high[0] >= count_14_entry[0]
                    )
                    count_14_sl_touched = (
                        self.low[0] <= count_14_sl[0]
                        if count_14_side[0] == 1.0 else
                        self.high[0] >= count_14_sl[0]
                    )
                    count_14_tp_touched = (
                        self.high[0] >= count_14_tp[0]
                        if count_14_side[0] == 1.0 else
                        self.low[0] <= count_14_tp[0]
                    )
                    if count_14_sl_touched or count_14_tp_touched:
                        if count_14_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_14_side[0] = 0.0
                        count_14_entry[0] = nan
                        count_14_sl[0] = nan
                        count_14_tp[0] = nan
                        count_14_day[0] = nan
                        count_14_bar[0] = -1.0
                    elif count_14_entry_touched:
                        if count_14_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_14_side[0] = 0.0
                        count_14_entry[0] = nan
                        count_14_sl[0] = nan
                        count_14_tp[0] = nan
                        count_14_day[0] = nan
                        count_14_bar[0] = -1.0

                if count_15_side[0] != 0.0 and self.bar_index > count_15_bar[0]:
                    count_15_entry_touched = (
                        self.low[0] <= count_15_entry[0]
                        if count_15_side[0] == 1.0 else
                        self.high[0] >= count_15_entry[0]
                    )
                    count_15_sl_touched = (
                        self.low[0] <= count_15_sl[0]
                        if count_15_side[0] == 1.0 else
                        self.high[0] >= count_15_sl[0]
                    )
                    count_15_tp_touched = (
                        self.high[0] >= count_15_tp[0]
                        if count_15_side[0] == 1.0 else
                        self.low[0] <= count_15_tp[0]
                    )
                    if count_15_sl_touched or count_15_tp_touched:
                        if count_15_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_15_side[0] = 0.0
                        count_15_entry[0] = nan
                        count_15_sl[0] = nan
                        count_15_tp[0] = nan
                        count_15_day[0] = nan
                        count_15_bar[0] = -1.0
                    elif count_15_entry_touched:
                        if count_15_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_15_side[0] = 0.0
                        count_15_entry[0] = nan
                        count_15_sl[0] = nan
                        count_15_tp[0] = nan
                        count_15_day[0] = nan
                        count_15_bar[0] = -1.0

                if count_16_side[0] != 0.0 and self.bar_index > count_16_bar[0]:
                    count_16_entry_touched = (
                        self.low[0] <= count_16_entry[0]
                        if count_16_side[0] == 1.0 else
                        self.high[0] >= count_16_entry[0]
                    )
                    count_16_sl_touched = (
                        self.low[0] <= count_16_sl[0]
                        if count_16_side[0] == 1.0 else
                        self.high[0] >= count_16_sl[0]
                    )
                    count_16_tp_touched = (
                        self.high[0] >= count_16_tp[0]
                        if count_16_side[0] == 1.0 else
                        self.low[0] <= count_16_tp[0]
                    )
                    if count_16_sl_touched or count_16_tp_touched:
                        if count_16_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_16_side[0] = 0.0
                        count_16_entry[0] = nan
                        count_16_sl[0] = nan
                        count_16_tp[0] = nan
                        count_16_day[0] = nan
                        count_16_bar[0] = -1.0
                    elif count_16_entry_touched:
                        if count_16_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_16_side[0] = 0.0
                        count_16_entry[0] = nan
                        count_16_sl[0] = nan
                        count_16_tp[0] = nan
                        count_16_day[0] = nan
                        count_16_bar[0] = -1.0

                if count_17_side[0] != 0.0 and self.bar_index > count_17_bar[0]:
                    count_17_entry_touched = (
                        self.low[0] <= count_17_entry[0]
                        if count_17_side[0] == 1.0 else
                        self.high[0] >= count_17_entry[0]
                    )
                    count_17_sl_touched = (
                        self.low[0] <= count_17_sl[0]
                        if count_17_side[0] == 1.0 else
                        self.high[0] >= count_17_sl[0]
                    )
                    count_17_tp_touched = (
                        self.high[0] >= count_17_tp[0]
                        if count_17_side[0] == 1.0 else
                        self.low[0] <= count_17_tp[0]
                    )
                    if count_17_sl_touched or count_17_tp_touched:
                        if count_17_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_17_side[0] = 0.0
                        count_17_entry[0] = nan
                        count_17_sl[0] = nan
                        count_17_tp[0] = nan
                        count_17_day[0] = nan
                        count_17_bar[0] = -1.0
                    elif count_17_entry_touched:
                        if count_17_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_17_side[0] = 0.0
                        count_17_entry[0] = nan
                        count_17_sl[0] = nan
                        count_17_tp[0] = nan
                        count_17_day[0] = nan
                        count_17_bar[0] = -1.0

                if count_18_side[0] != 0.0 and self.bar_index > count_18_bar[0]:
                    count_18_entry_touched = (
                        self.low[0] <= count_18_entry[0]
                        if count_18_side[0] == 1.0 else
                        self.high[0] >= count_18_entry[0]
                    )
                    count_18_sl_touched = (
                        self.low[0] <= count_18_sl[0]
                        if count_18_side[0] == 1.0 else
                        self.high[0] >= count_18_sl[0]
                    )
                    count_18_tp_touched = (
                        self.high[0] >= count_18_tp[0]
                        if count_18_side[0] == 1.0 else
                        self.low[0] <= count_18_tp[0]
                    )
                    if count_18_sl_touched or count_18_tp_touched:
                        if count_18_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_18_side[0] = 0.0
                        count_18_entry[0] = nan
                        count_18_sl[0] = nan
                        count_18_tp[0] = nan
                        count_18_day[0] = nan
                        count_18_bar[0] = -1.0
                    elif count_18_entry_touched:
                        if count_18_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_18_side[0] = 0.0
                        count_18_entry[0] = nan
                        count_18_sl[0] = nan
                        count_18_tp[0] = nan
                        count_18_day[0] = nan
                        count_18_bar[0] = -1.0

                if count_19_side[0] != 0.0 and self.bar_index > count_19_bar[0]:
                    count_19_entry_touched = (
                        self.low[0] <= count_19_entry[0]
                        if count_19_side[0] == 1.0 else
                        self.high[0] >= count_19_entry[0]
                    )
                    count_19_sl_touched = (
                        self.low[0] <= count_19_sl[0]
                        if count_19_side[0] == 1.0 else
                        self.high[0] >= count_19_sl[0]
                    )
                    count_19_tp_touched = (
                        self.high[0] >= count_19_tp[0]
                        if count_19_side[0] == 1.0 else
                        self.low[0] <= count_19_tp[0]
                    )
                    if count_19_sl_touched or count_19_tp_touched:
                        if count_19_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_19_side[0] = 0.0
                        count_19_entry[0] = nan
                        count_19_sl[0] = nan
                        count_19_tp[0] = nan
                        count_19_day[0] = nan
                        count_19_bar[0] = -1.0
                    elif count_19_entry_touched:
                        if count_19_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_19_side[0] = 0.0
                        count_19_entry[0] = nan
                        count_19_sl[0] = nan
                        count_19_tp[0] = nan
                        count_19_day[0] = nan
                        count_19_bar[0] = -1.0

                if count_20_side[0] != 0.0 and self.bar_index > count_20_bar[0]:
                    count_20_entry_touched = (
                        self.low[0] <= count_20_entry[0]
                        if count_20_side[0] == 1.0 else
                        self.high[0] >= count_20_entry[0]
                    )
                    count_20_sl_touched = (
                        self.low[0] <= count_20_sl[0]
                        if count_20_side[0] == 1.0 else
                        self.high[0] >= count_20_sl[0]
                    )
                    count_20_tp_touched = (
                        self.high[0] >= count_20_tp[0]
                        if count_20_side[0] == 1.0 else
                        self.low[0] <= count_20_tp[0]
                    )
                    if count_20_sl_touched or count_20_tp_touched:
                        if count_20_day[0] == self._selected_report_day_key:
                            report_inactive_trades[0] = report_inactive_trades[0] + 1.0
                        count_20_side[0] = 0.0
                        count_20_entry[0] = nan
                        count_20_sl[0] = nan
                        count_20_tp[0] = nan
                        count_20_day[0] = nan
                        count_20_bar[0] = -1.0
                    elif count_20_entry_touched:
                        if count_20_day[0] == self._selected_report_day_key:
                            report_active_trades[0] = report_active_trades[0] + 1.0
                        count_20_side[0] = 0.0
                        count_20_entry[0] = nan
                        count_20_sl[0] = nan
                        count_20_tp[0] = nan
                        count_20_day[0] = nan
                        count_20_bar[0] = -1.0

                if not rr_setting_changed:
                    count_sell_ready = sell_condition or sell_breakout_pullback_ready
                    count_buy_ready = buy_condition or buy_breakout_pullback_ready

                    if count_sell_ready and not count_buy_ready:
                        count_new_entry = candidate_entry_price
                        count_recent_high = max([
                            self.high[0], self.high[1], self.high[2], self.high[3],
                            self.high[4], self.high[5], self.high[6], self.high[7]
                        ])
                        count_stop_buffer = max(candle_range * 0.25, abs(count_new_entry) * 0.00005)
                        count_new_stop = max(count_recent_high, count_new_entry + count_stop_buffer)
                        count_new_risk = count_new_stop - count_new_entry
                        count_new_distance = abs(count_new_entry - count_new_stop)
                        count_new_side = -1.0
                    elif count_buy_ready:
                        count_new_entry = candidate_entry_price
                        count_recent_low = min([
                            self.low[0], self.low[1], self.low[2], self.low[3],
                            self.low[4], self.low[5], self.low[6], self.low[7]
                        ])
                        count_stop_buffer = max(candle_range * 0.25, abs(count_new_entry) * 0.00005)
                        count_new_stop = min(count_recent_low, count_new_entry - count_stop_buffer)
                        count_new_risk = count_new_entry - count_new_stop
                        count_new_distance = abs(count_new_entry - count_new_stop)
                        count_new_side = 1.0
                    else:
                        count_new_risk = 0.0
                        count_new_distance = 0.0

                    count_new_risk_per_lot = count_new_distance * self.contract_size
                    count_new_lot = 0.0
                    if count_new_risk_per_lot > 0.0 and risk_budget_cash > 0.0:
                        count_new_lot = int((risk_budget_cash / count_new_risk_per_lot) * 100.0) / 100.0

                    if (
                        count_new_side != 0.0
                        and count_new_risk > 0.0
                        and count_new_distance <= maximum_allowed_sl_distance
                        and count_new_lot >= 0.01
                    ):
                        if count_1_side[0] == 0.0:
                            count_1_side[0] = count_new_side
                            count_1_entry[0] = count_new_entry
                            count_1_sl[0] = count_new_stop
                            count_1_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_1_day[0] = current_ist_day_key
                            count_1_bar[0] = float(self.bar_index)
                        elif count_2_side[0] == 0.0:
                            count_2_side[0] = count_new_side
                            count_2_entry[0] = count_new_entry
                            count_2_sl[0] = count_new_stop
                            count_2_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_2_day[0] = current_ist_day_key
                            count_2_bar[0] = float(self.bar_index)
                        elif count_3_side[0] == 0.0:
                            count_3_side[0] = count_new_side
                            count_3_entry[0] = count_new_entry
                            count_3_sl[0] = count_new_stop
                            count_3_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_3_day[0] = current_ist_day_key
                            count_3_bar[0] = float(self.bar_index)
                        elif count_4_side[0] == 0.0:
                            count_4_side[0] = count_new_side
                            count_4_entry[0] = count_new_entry
                            count_4_sl[0] = count_new_stop
                            count_4_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_4_day[0] = current_ist_day_key
                            count_4_bar[0] = float(self.bar_index)
                        elif count_5_side[0] == 0.0:
                            count_5_side[0] = count_new_side
                            count_5_entry[0] = count_new_entry
                            count_5_sl[0] = count_new_stop
                            count_5_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_5_day[0] = current_ist_day_key
                            count_5_bar[0] = float(self.bar_index)
                        elif count_6_side[0] == 0.0:
                            count_6_side[0] = count_new_side
                            count_6_entry[0] = count_new_entry
                            count_6_sl[0] = count_new_stop
                            count_6_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_6_day[0] = current_ist_day_key
                            count_6_bar[0] = float(self.bar_index)
                        elif count_7_side[0] == 0.0:
                            count_7_side[0] = count_new_side
                            count_7_entry[0] = count_new_entry
                            count_7_sl[0] = count_new_stop
                            count_7_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_7_day[0] = current_ist_day_key
                            count_7_bar[0] = float(self.bar_index)
                        elif count_8_side[0] == 0.0:
                            count_8_side[0] = count_new_side
                            count_8_entry[0] = count_new_entry
                            count_8_sl[0] = count_new_stop
                            count_8_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_8_day[0] = current_ist_day_key
                            count_8_bar[0] = float(self.bar_index)
                        elif count_9_side[0] == 0.0:
                            count_9_side[0] = count_new_side
                            count_9_entry[0] = count_new_entry
                            count_9_sl[0] = count_new_stop
                            count_9_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_9_day[0] = current_ist_day_key
                            count_9_bar[0] = float(self.bar_index)
                        elif count_10_side[0] == 0.0:
                            count_10_side[0] = count_new_side
                            count_10_entry[0] = count_new_entry
                            count_10_sl[0] = count_new_stop
                            count_10_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_10_day[0] = current_ist_day_key
                            count_10_bar[0] = float(self.bar_index)
                        elif count_11_side[0] == 0.0:
                            count_11_side[0] = count_new_side
                            count_11_entry[0] = count_new_entry
                            count_11_sl[0] = count_new_stop
                            count_11_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_11_day[0] = current_ist_day_key
                            count_11_bar[0] = float(self.bar_index)
                        elif count_12_side[0] == 0.0:
                            count_12_side[0] = count_new_side
                            count_12_entry[0] = count_new_entry
                            count_12_sl[0] = count_new_stop
                            count_12_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_12_day[0] = current_ist_day_key
                            count_12_bar[0] = float(self.bar_index)
                        elif count_13_side[0] == 0.0:
                            count_13_side[0] = count_new_side
                            count_13_entry[0] = count_new_entry
                            count_13_sl[0] = count_new_stop
                            count_13_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_13_day[0] = current_ist_day_key
                            count_13_bar[0] = float(self.bar_index)
                        elif count_14_side[0] == 0.0:
                            count_14_side[0] = count_new_side
                            count_14_entry[0] = count_new_entry
                            count_14_sl[0] = count_new_stop
                            count_14_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_14_day[0] = current_ist_day_key
                            count_14_bar[0] = float(self.bar_index)
                        elif count_15_side[0] == 0.0:
                            count_15_side[0] = count_new_side
                            count_15_entry[0] = count_new_entry
                            count_15_sl[0] = count_new_stop
                            count_15_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_15_day[0] = current_ist_day_key
                            count_15_bar[0] = float(self.bar_index)
                        elif count_16_side[0] == 0.0:
                            count_16_side[0] = count_new_side
                            count_16_entry[0] = count_new_entry
                            count_16_sl[0] = count_new_stop
                            count_16_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_16_day[0] = current_ist_day_key
                            count_16_bar[0] = float(self.bar_index)
                        elif count_17_side[0] == 0.0:
                            count_17_side[0] = count_new_side
                            count_17_entry[0] = count_new_entry
                            count_17_sl[0] = count_new_stop
                            count_17_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_17_day[0] = current_ist_day_key
                            count_17_bar[0] = float(self.bar_index)
                        elif count_18_side[0] == 0.0:
                            count_18_side[0] = count_new_side
                            count_18_entry[0] = count_new_entry
                            count_18_sl[0] = count_new_stop
                            count_18_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_18_day[0] = current_ist_day_key
                            count_18_bar[0] = float(self.bar_index)
                        elif count_19_side[0] == 0.0:
                            count_19_side[0] = count_new_side
                            count_19_entry[0] = count_new_entry
                            count_19_sl[0] = count_new_stop
                            count_19_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_19_day[0] = current_ist_day_key
                            count_19_bar[0] = float(self.bar_index)
                        elif count_20_side[0] == 0.0:
                            count_20_side[0] = count_new_side
                            count_20_entry[0] = count_new_entry
                            count_20_sl[0] = count_new_stop
                            count_20_tp[0] = (
                                count_new_entry + count_new_risk * rr_multiplier
                                if count_new_side == 1.0 else
                                count_new_entry - count_new_risk * rr_multiplier
                            )
                            count_20_day[0] = current_ist_day_key
                            count_20_bar[0] = float(self.bar_index)
                        # If all 20 slots are occupied, do not overwrite an unresolved setup.
            # ================================================
            # NEW PRIMARY ENTRY
            # ================================================

            # Never commit an entry, set active trade state, or expose an
            # absolute entry marker while this candle is still forming.
            # Setup conditions may develop intrabar, but the final entry/SL/TP
            # calculation is committed only on the candle-close callback.
            if (
                self.is_closed_bar and side[0] == 0.0
                and pending_trade_side[0] == 0.0 and not trade_exited
            ):

                # Preserve the original signal conditions without a deviation
                # filter. Entry 1 uses the confirmation candle midpoint.
                sell_entry_ready = sell_condition or sell_breakout_pullback_ready
                buy_entry_ready = buy_condition or buy_breakout_pullback_ready

                if sell_entry_ready and not buy_entry_ready:

                    recent_high = max([
                        self.high[0], self.high[1],
                        self.high[2], self.high[3],
                        self.high[4], self.high[5],
                        self.high[6], self.high[7]
                    ])

                    # Preserve the original midpoint setup and sizing exactly.
                    # The midpoint determines the original SL, TP and total lot.
                    entry_price = candidate_entry_price

                    if sell_breakout_pullback_ready:
                        sell_reason = 'BREAKOUT + VOLUME PULLBACK'

                    stop_price = recent_high
                    entry_stop_buffer = max(
                        candle_range * 0.25,
                        abs(entry_price) * 0.00005
                    )
                    stop_price = max(
                        stop_price,
                        entry_price + entry_stop_buffer
                    )

                    risk = stop_price - entry_price
                    sl_distance = abs(entry_price - stop_price)
                    risk_per_one_lot = sl_distance * self.contract_size
                    calculated_lot = 0.0
                    calculated_risk_cash = nan

                    if risk_per_one_lot > 0.0 and risk_budget_cash > 0.0:
                        raw_lot = risk_budget_cash / risk_per_one_lot
                        calculated_lot = int(raw_lot * 100.0) / 100.0
                        calculated_risk_cash = (
                            calculated_lot * risk_per_one_lot
                        )

                    # Allocate half of the dollar risk budget to the midpoint leg.
                    # The remaining budget is reserved for the immediate leg after midpoint fill.
                    midpoint_risk_per_lot = sl_distance * self.contract_size
                    mid_lot = 0.0
                    if midpoint_risk_per_lot > 0.0 and risk_budget_cash > 0.0:
                        midpoint_half_budget = risk_budget_cash * 0.50
                        mid_lot = int((midpoint_half_budget / midpoint_risk_per_lot) * 100.0) / 100.0

                    mid_risk_cash_value = mid_lot * midpoint_risk_per_lot

                    if (
                        risk > 0.0
                        and sl_distance <= maximum_allowed_sl_distance
                        and mid_lot >= 0.01
                        and mid_risk_cash_value <= risk_budget_cash
                    ):
                        target_price = entry_price - risk * rr_multiplier

                        # Arm only a pending midpoint order. No active side,
                        # trade P/L, or immediate entry is recorded yet.
                        pending_trade_side[0] = -1.0
                        pending_trade_entry[0] = entry_price
                        pending_mid_entry[0] = entry_price
                        pending_trade_sl[0] = stop_price
                        pending_trade_tp[0] = target_price
                        pending_trade_lot[0] = mid_lot
                        pending_trade_risk_cash[0] = mid_risk_cash_value
                        pending_trade_setup_day[0] = current_ist_day_key
                        pending_trade_setup_bar[0] = float(self.bar_index)

                        entry[0] = nan
                        midpoint_master_entry[0] = entry_price
                        early_leg_entry[0] = entry_price
                        early_leg_lot[0] = 0.0
                        mid_leg_lot[0] = mid_lot
                        mid_leg_active[0] = 0.0
                        early_leg_closed[0] = 0.0
                        early_leg_pnl[0] = 0.0
                        mid_leg_pnl[0] = 0.0
                        setup_risk_budget[0] = risk_budget_cash
                        sl[0] = stop_price
                        tp[0] = target_price
                        side[0] = 0.0
                        trade_lot[0] = nan
                        trade_risk_cash[0] = nan
                        original_risk_distance[0] = sl_distance
                        favorable_extreme[0] = entry_price
                        trail_candidate[0] = nan
                        trail_confirm_count[0] = 0.0
                        trail_stage[0] = 0.0
                        trail_last_update_bar[0] = -1.0
                        early_exit_warned[0] = 0.0
                        entry_count[0] = 0.0
                        last_entry_bar[0] = -1.0
                        last_entry_price[0] = nan
                        entry_label_time[0] = self.time[0]
                        pending_early_entry[0] = nan
                        sell_signal = True

                        pending_buy[0] = 0.0
                        pending_buy_average[0] = nan
                        pending_buy_low[0] = nan
                        pending_buy_bar[0] = -1.0
                        pending_sell[0] = 0.0
                        pending_sell_average[0] = nan
                        pending_sell_high[0] = nan
                        pending_sell_bar[0] = -1.0

                elif buy_entry_ready:

                    recent_low = min([
                        self.low[0], self.low[1],
                        self.low[2], self.low[3],
                        self.low[4], self.low[5],
                        self.low[6], self.low[7]
                    ])

                    # Preserve the original midpoint setup and sizing exactly.
                    # The midpoint determines the original SL, TP and total lot.
                    entry_price = candidate_entry_price

                    if buy_breakout_pullback_ready:
                        buy_reason = 'BREAKOUT + VOLUME PULLBACK'

                    stop_price = recent_low
                    entry_stop_buffer = max(
                        candle_range * 0.25,
                        abs(entry_price) * 0.00005
                    )
                    stop_price = min(
                        stop_price,
                        entry_price - entry_stop_buffer
                    )

                    risk = entry_price - stop_price
                    sl_distance = abs(entry_price - stop_price)
                    risk_per_one_lot = sl_distance * self.contract_size
                    calculated_lot = 0.0
                    calculated_risk_cash = nan

                    if risk_per_one_lot > 0.0 and risk_budget_cash > 0.0:
                        raw_lot = risk_budget_cash / risk_per_one_lot
                        calculated_lot = int(raw_lot * 100.0) / 100.0
                        calculated_risk_cash = (
                            calculated_lot * risk_per_one_lot
                        )

                    # Allocate half of the dollar risk budget to the midpoint leg.
                    # The remaining budget is reserved for the immediate leg after midpoint fill.
                    midpoint_risk_per_lot = sl_distance * self.contract_size
                    mid_lot = 0.0
                    if midpoint_risk_per_lot > 0.0 and risk_budget_cash > 0.0:
                        midpoint_half_budget = risk_budget_cash * 0.50
                        mid_lot = int((midpoint_half_budget / midpoint_risk_per_lot) * 100.0) / 100.0

                    mid_risk_cash_value = mid_lot * midpoint_risk_per_lot

                    if (
                        risk > 0.0
                        and sl_distance <= maximum_allowed_sl_distance
                        and mid_lot >= 0.01
                        and mid_risk_cash_value <= risk_budget_cash
                    ):
                        target_price = entry_price + risk * rr_multiplier

                        # Arm only a pending midpoint order. No active side,
                        # trade P/L, or immediate entry is recorded yet.
                        pending_trade_side[0] = 1.0
                        pending_trade_entry[0] = entry_price
                        pending_mid_entry[0] = entry_price
                        pending_trade_sl[0] = stop_price
                        pending_trade_tp[0] = target_price
                        pending_trade_lot[0] = mid_lot
                        pending_trade_risk_cash[0] = mid_risk_cash_value
                        pending_trade_setup_day[0] = current_ist_day_key
                        pending_trade_setup_bar[0] = float(self.bar_index)

                        entry[0] = nan
                        midpoint_master_entry[0] = entry_price
                        early_leg_entry[0] = entry_price
                        early_leg_lot[0] = 0.0
                        mid_leg_lot[0] = mid_lot
                        mid_leg_active[0] = 0.0
                        early_leg_closed[0] = 0.0
                        early_leg_pnl[0] = 0.0
                        mid_leg_pnl[0] = 0.0
                        setup_risk_budget[0] = risk_budget_cash
                        sl[0] = stop_price
                        tp[0] = target_price
                        side[0] = 0.0
                        trade_lot[0] = nan
                        trade_risk_cash[0] = nan
                        original_risk_distance[0] = sl_distance
                        favorable_extreme[0] = entry_price
                        trail_candidate[0] = nan
                        trail_confirm_count[0] = 0.0
                        trail_stage[0] = 0.0
                        trail_last_update_bar[0] = -1.0
                        early_exit_warned[0] = 0.0
                        entry_count[0] = 0.0
                        last_entry_bar[0] = -1.0
                        last_entry_price[0] = nan
                        entry_label_time[0] = self.time[0]
                        pending_early_entry[0] = nan
                        buy_signal = True

                        pending_buy[0] = 0.0
                        pending_buy_average[0] = nan
                        pending_buy_low[0] = nan
                        pending_buy_bar[0] = -1.0
                        pending_sell[0] = 0.0
                        pending_sell_average[0] = nan
                        pending_sell_high[0] = nan
                        pending_sell_bar[0] = -1.0

                        if not (
                            self.delete_setup == 'Primary BUY'
                            and self.bar_index == self.delete_bar_index
                        ):

                            if self.is_closed_bar:

                                pass

        # ====================================================
        # ONE COMBINED TRADE DESCRIPTION BOX
        # ====================================================

        new_trade_entry_event = (
            last_entry_bar[0] == self.bar_index
        )

        # ====================================================
        # LOT LABEL ONLY AT TRADE ENTRY
        # PROFIT / LOSS LABELS ARE DRAWN ONLY AFTER EXIT
        # ====================================================

        if (
            self.show_entry_descriptions
            and new_trade_entry_event
            and side[0] != 0.0
        ):

            is_buy = side[0] == 1.0

            trade_symbol = ''

            entry1_description_reason = (
                buy_reason if is_buy else sell_reason
            )

            entry2_description_reason = ''
            addon_zone_reason = ''

            if is_buy:

                if bullish_breakout_volume_setup or buy_reason == 'BREAKOUT + VOLUME PULLBACK':
                    entry2_description_reason = 'Breakout Pullback'

                elif bullish_engulfing:
                    entry2_description_reason = 'Engulf'

                elif bullish_hammer:
                    entry2_description_reason = 'Hammer'

                elif morning_star:
                    entry2_description_reason = 'MStar'

                elif bullish_rejection:
                    entry2_description_reason = 'Reject'

                elif bullish_break_previous:
                    entry2_description_reason = 'BrkHi'

                elif bullish_strong_body:
                    entry2_description_reason = 'Strong'

                else:
                    entry2_description_reason = 'PA'

                if support_zone:
                    entry2_description_reason += ' + Support'
                    addon_zone_reason += ' + Support'

                if bullish_ob_touch:
                    entry2_description_reason += ' + OB'
                    addon_zone_reason += ' + OB'

                if bullish_fvg_touch:
                    entry2_description_reason += ' + FVG'
                    addon_zone_reason += ' + FVG'

                if self.close[0] > ema9[0] and self.close[0] > ema20[0]:
                    entry2_description_reason += ' + EMA'

                if rsi[0] > rsi[1] and rsi[0] > 40:
                    entry2_description_reason += ' + RSI'

            else:

                if bearish_breakout_volume_setup or sell_reason == 'BREAKOUT + VOLUME PULLBACK':
                    entry2_description_reason = 'Breakout Pullback'

                elif bearish_engulfing or bearish_close_momentum:
                    entry2_description_reason = 'Engulf'

                elif bearish_shooting_star:
                    entry2_description_reason = 'SStar'

                elif evening_star:
                    entry2_description_reason = 'Evening Star'

                elif bearish_rejection:
                    entry2_description_reason = 'Reject'

                elif bearish_break_previous:
                    entry2_description_reason = 'BrkLo'

                elif bearish_strong_body:
                    entry2_description_reason = 'Strong'

                else:
                    entry2_description_reason = 'PA'

                if resistance_zone:
                    entry2_description_reason += ' + Resistance'
                    addon_zone_reason += ' + Resistance'

                if bearish_ob_touch:
                    entry2_description_reason += ' + OB'
                    addon_zone_reason += ' + OB'

                if bearish_fvg_touch:
                    entry2_description_reason += ' + FVG'
                    addon_zone_reason += ' + FVG'

                if self.close[0] < ema9[0] and self.close[0] < ema20[0]:
                    entry2_description_reason += ' + EMA'

                if rsi[0] < rsi[1] and rsi[0] < 60:
                    entry2_description_reason += ' + RSI'

            entry345_description_reason = 'PA' + addon_zone_reason

            sl_text = ' | SL ' + str(round(sl[0], 2))
            tp_text = ' | TP ' + str(round(tp[0], 2))
            lot_text = ''

            if trade_lot[0] == trade_lot[0]:
                lot_text = (
                    ' | TOTAL LOT ' + str(round(trade_lot[0], 2))
                    + ' | RISK $'
                    + str(round(trade_risk_cash[0], 2))
                )

            combined_trade_description = ''

            if entry[0] == entry[0]:

                combined_trade_description += (
                    trade_symbol + ' 1 @ ' + str(round(entry[0], 2))
                    + sl_text + tp_text + lot_text
                    + ' | Reason: ' + entry1_description_reason
                )

            if second_entry_price[0] == second_entry_price[0]:

                if combined_trade_description != '':
                    combined_trade_description += '\n'

                combined_trade_description += (
                    trade_symbol + ' 2 @ '
                    + str(round(second_entry_price[0], 2))
                    + sl_text + tp_text
                    + ' | Reason: ' + entry2_description_reason
                )

            if third_entry_price[0] == third_entry_price[0]:

                if combined_trade_description != '':
                    combined_trade_description += '\n'

                combined_trade_description += (
                    trade_symbol + ' 3 @ '
                    + str(round(third_entry_price[0], 2))
                    + sl_text + tp_text
                    + ' | Reason: ' + entry345_description_reason
                )

            if fourth_entry_price[0] == fourth_entry_price[0]:

                if combined_trade_description != '':
                    combined_trade_description += '\n'

                combined_trade_description += (
                    trade_symbol + ' 4 @ '
                    + str(round(fourth_entry_price[0], 2))
                    + sl_text + tp_text
                    + ' | Reason: ' + entry345_description_reason
                )

            if fifth_entry_price[0] == fifth_entry_price[0]:

                if combined_trade_description != '':
                    combined_trade_description += '\n'

                combined_trade_description += (
                    trade_symbol + ' 5 @ '
                    + str(round(fifth_entry_price[0], 2))
                    + sl_text + tp_text
                    + ' | Reason: ' + entry345_description_reason
                )

            if self.is_closed_bar:

                pass

        # ====================================================
        # CURRENT CHART TIMEFRAME DAILY REPORT
        # CLOSED TRADES ONLY - SPREADSHEET STYLE
        # ====================================================

        if self.show_daily_report and self.is_last_bar:

            chart_minutes = self.time_frame.to_minutes()

            timeframe_label = ''

            if chart_minutes < 60:
                timeframe_label = str(chart_minutes) + ' min'
            elif chart_minutes == 60:
                timeframe_label = '1 hour'
            elif chart_minutes % 60 == 0 and chart_minutes < 1440:
                timeframe_label = str(int(chart_minutes / 60)) + ' hours'
            elif chart_minutes >= 1440 and chart_minutes % 1440 == 0:
                timeframe_label = str(int(chart_minutes / 1440)) + ' day'
            else:
                timeframe_label = str(chart_minutes) + ' min'

            sl_count = int(report_sl[0])
            tp_count = int(report_tp[0])
            trailing_sl_count = int(report_trailing_sl[0])
            active_trades = int(report_active_trades[0])
            inactive_trades = int(report_inactive_trades[0])
            total_trades = active_trades + inactive_trades
            total_exits = sl_count + tp_count + trailing_sl_count

            win_rate = 0.0
            if total_exits > 0:
                win_rate = (tp_count / total_exits) * 100.0

            report_year = int(self.report_date / 10000)
            report_month = int((self.report_date % 10000) / 100)
            report_day = int(self.report_date % 100)

            report_day_text = str(report_day)
            report_month_text = str(report_month)

            if report_day < 10:
                report_day_text = '0' + report_day_text

            if report_month < 10:
                report_month_text = '0' + report_month_text

            date_label = (
                report_day_text + '-'
                + report_month_text + '-'
                + str(report_year)
            )

            label_width = 44
            value_width = 18

            top_border = (
                '+' + ('-' * (label_width + 2))
                + '+' + ('-' * (value_width + 2)) + '+'
            )

            header_row = (
                '| ' + '𝗞𝗦 𝗧𝗥𝗔𝗗𝗘𝗥 𝗗𝗘𝗦𝗞 - 𝗗𝗔𝗜𝗟𝗬 / 𝗠𝗢𝗡𝗧𝗛𝗟𝗬 𝗣/𝗟'.ljust(label_width) + ' | '
                + 'RESULT'.ljust(value_width) + ' |'
            )

            date_row = (
                '| ' + 'Date'.ljust(label_width) + ' | '
                + date_label.ljust(value_width) + ' |'
            )

            timeframe_row = (
                '| ' + 'Time frame'.ljust(label_width) + ' | '
                + timeframe_label.ljust(value_width) + ' |'
            )

            active_row = (
                '| ' + 'Active Trades'.ljust(label_width) + ' | '
                + str(active_trades).ljust(value_width) + ' |'
            )
            inactive_row = (
                '| ' + 'Inactive Trades'.ljust(label_width) + ' | '
                + str(inactive_trades).ljust(value_width) + ' |'
            )
            total_row = (
                '| ' + 'Total trades'.ljust(label_width) + ' | '
                + str(total_trades).ljust(value_width) + ' |'
            )

            active_pnl_row = (
                '| ' + 'Active Trade P/L'.ljust(label_width) + ' | '
                + ('$' + str(round(report_active_pnl[0], 2))).ljust(value_width) + ' |'
            )
            inactive_pnl_row = (
                '| ' + 'Inactive Trade P/L'.ljust(label_width) + ' | '
                + ('$' + str(round(report_inactive_pnl[0], 2))).ljust(value_width) + ' |'
            )

            sl_row = (
                '| ' + 'StopLoss'.ljust(label_width) + ' | '
                + str(sl_count).ljust(value_width) + ' |'
            )

            tp_row = (
                '| ' + 'Target Hit'.ljust(label_width) + ' | '
                + str(tp_count).ljust(value_width) + ' |'
            )

            trailing_sl_text = (
                str(trailing_sl_count) if trailing_sl_count > 0
                else 'No trades hit'
            )
            trailing_sl_row = (
                '| ' + 'Trailing SL Hit'.ljust(label_width) + ' | '
                + trailing_sl_text.ljust(value_width) + ' |'
            )
            win_row = (
                '| ' + 'Win Rate'.ljust(label_width) + ' | '
                + (str(int(round(win_rate))) + '%').ljust(value_width) + ' |'
            )

            rr_row = (
                '| ' + 'Risk Reward'.ljust(label_width) + ' | '
                + self.risk_reward.ljust(value_width) + ' |'
            )

            risk_mode_text = 'REDUCED 3% + 1%' if reduced_risk_mode[0] == 1.0 else 'NORMAL 5% + 2%'
            risk_mode_row = (
                '| ' + 'Current Risk Mode'.ljust(label_width) + ' | '
                + risk_mode_text.ljust(value_width) + ' |'
            )

            net_profit_row = (
                '| ' + 'Daily Net P/L'.ljust(label_width) + ' | '
                + ('$' + str(round(report_net_profit[0], 2))).ljust(value_width) + ' |'
            )

            monthly_net_profit_row = (
                '| ' + 'Monthly Net P/L'.ljust(label_width) + ' | '
                + ('$' + str(round(monthly_net_profit[0], 2))).ljust(value_width) + ' |'
            )

            report_text = (
                top_border + '\n'
                + header_row + '\n'
                + top_border + '\n'
                + date_row + '\n'
                + timeframe_row + '\n'
                + active_row + '\n'
                + inactive_row + '\n'
                + total_row + '\n'
                + active_pnl_row + '\n'
                + inactive_pnl_row + '\n'
                + sl_row + '\n'
                + tp_row + '\n'
                + trailing_sl_row + '\n'
                + win_row + '\n'
                + rr_row + '\n'
                + risk_mode_row + '\n'
                + net_profit_row + '\n'
                + monthly_net_profit_row
            )

            # Optional daily breakdown for the selected month, through the current IST date.
            if self.show_monthly_daily_breakdown:
                report_text += '\n' + top_border
                report_text += '\n| ' + 'MONTHLY DAILY NET P/L'.ljust(label_width) + ' | ' + 'AMOUNT'.ljust(value_width) + ' |'
                report_text += '\n' + top_border

                days_in_selected_month = int(
                    self._selected_report_month_end_key
                    - self._selected_report_month_start_key
                )
                current_month_day_limit = int(
                    max(
                        0.0,
                        min(
                            float(days_in_selected_month),
                            current_ist_day_key - self._selected_report_month_start_key + 1.0
                        )
                    )
                )

                month_names = [
                    '', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
                ]
                selected_month_name = month_names[report_month]

                for day_number in range(1, current_month_day_limit + 1):
                    day_profit = 0.0

                    if day_number == 1:
                        day_profit = monthly_day_01_profit[0]
                    elif day_number == 2:
                        day_profit = monthly_day_02_profit[0]
                    elif day_number == 3:
                        day_profit = monthly_day_03_profit[0]
                    elif day_number == 4:
                        day_profit = monthly_day_04_profit[0]
                    elif day_number == 5:
                        day_profit = monthly_day_05_profit[0]
                    elif day_number == 6:
                        day_profit = monthly_day_06_profit[0]
                    elif day_number == 7:
                        day_profit = monthly_day_07_profit[0]
                    elif day_number == 8:
                        day_profit = monthly_day_08_profit[0]
                    elif day_number == 9:
                        day_profit = monthly_day_09_profit[0]
                    elif day_number == 10:
                        day_profit = monthly_day_10_profit[0]
                    elif day_number == 11:
                        day_profit = monthly_day_11_profit[0]
                    elif day_number == 12:
                        day_profit = monthly_day_12_profit[0]
                    elif day_number == 13:
                        day_profit = monthly_day_13_profit[0]
                    elif day_number == 14:
                        day_profit = monthly_day_14_profit[0]
                    elif day_number == 15:
                        day_profit = monthly_day_15_profit[0]
                    elif day_number == 16:
                        day_profit = monthly_day_16_profit[0]
                    elif day_number == 17:
                        day_profit = monthly_day_17_profit[0]
                    elif day_number == 18:
                        day_profit = monthly_day_18_profit[0]
                    elif day_number == 19:
                        day_profit = monthly_day_19_profit[0]
                    elif day_number == 20:
                        day_profit = monthly_day_20_profit[0]
                    elif day_number == 21:
                        day_profit = monthly_day_21_profit[0]
                    elif day_number == 22:
                        day_profit = monthly_day_22_profit[0]
                    elif day_number == 23:
                        day_profit = monthly_day_23_profit[0]
                    elif day_number == 24:
                        day_profit = monthly_day_24_profit[0]
                    elif day_number == 25:
                        day_profit = monthly_day_25_profit[0]
                    elif day_number == 26:
                        day_profit = monthly_day_26_profit[0]
                    elif day_number == 27:
                        day_profit = monthly_day_27_profit[0]
                    elif day_number == 28:
                        day_profit = monthly_day_28_profit[0]
                    elif day_number == 29:
                        day_profit = monthly_day_29_profit[0]
                    elif day_number == 30:
                        day_profit = monthly_day_30_profit[0]
                    elif day_number == 31:
                        day_profit = monthly_day_31_profit[0]

                    daily_date_text = selected_month_name + ' ' + str(day_number)
                    daily_amount_text = '$' + str(round(day_profit, 2))
                    report_text += (
                        '\n| ' + daily_date_text.ljust(label_width)
                        + ' | ' + daily_amount_text.ljust(value_width) + ' |'
                    )

                report_text += '\n' + top_border
            else:
                report_text += '\n' + top_border

            self._daily_report_label.text = report_text
            self.chart.draw(self._daily_report_label)

        # Bar number is intentionally omitted from chart drawings.

        # ====================================================
        # PRIMARY ENTRY MARKER - RESTORED FROM ORIGINAL REPO
        # ====================================================

        marker_price = nan

        if (
            buy_signal
            and not (
                self.delete_setup == 'Primary BUY'
                and self.bar_index == self.delete_bar_index
            )
        ):
            marker_price = self.low[0] - entry_marker_offset

        elif (
            sell_signal
            and not (
                self.delete_setup == 'Primary SELL'
                and self.bar_index == self.delete_bar_index
            )
        ):
            marker_price = self.high[0] + entry_marker_offset

        marker_color = (
            color.RED
            if buy_signal or sell_signal
            else color.TRANSPARENT
        )

        # ====================================================
        # VISUAL TRADE LEVELS
        # Keep the planned Entry / SL / TP visible from the setup
        # candle while the order is pending. This is display-only;
        # internal active-trade calculations continue using entry/sl/tp.
        # ====================================================

        plot_entry_value = entry[0]
        plot_sl_value = sl[0]
        plot_tp_value = tp[0]

        if side[0] != 0.0:
            plot_entry_value = midpoint_master_entry[0]
            plot_sl_value = sl[0]
            plot_tp_value = tp[0]

        # ====================================================
        # OUTPUT
        # ====================================================

        return (
            ema9[0],
            ema20[0],
            ema50[0],
            ema200[0],

            plot_entry_value,
            second_entry_price[0],
            third_entry_price[0],
            fourth_entry_price[0],
            fifth_entry_price[0],

            plot_sl_value,
            plot_tp_value,

            plot.Fill(),
            plot.Fill(),

            plot.Marker(
                value=marker_price,
                color=marker_color
            )
        )

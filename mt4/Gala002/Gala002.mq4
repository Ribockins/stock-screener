//+------------------------------------------------------------------+
//|                                                    Gala002.mq4   |
//|                         Gala002 — Gold exhaustion EA (v2)        |
//|                         Impulse -> Overextension -> Slowdown     |
//|                         Modular MQL4 / MetaTrader 4              |
//+------------------------------------------------------------------+
#property strict
#property copyright "Gala002"
#property version   "2.00"
#property description "Weighted gold exhaustion scoring with modular protection."

// =====================================================
// INPUTS — GENERAL
// =====================================================

input bool   DebugMode              = false;
input bool   TradeOnlyGoldSymbols   = true;
input bool   UseNewBarOnly          = true;

input double LotSize                = 0.01;
input double TakeProfitPips         = 50;
input double StopLossPips           = 500;

input int    MaxTradesPerDay        = 7;
input int    MaxOpenTradesTotal     = 7;
input int    MaxSameDirectionOpen   = 2;
input int    MinMinutesBetweenTrades = 25;


// =====================================================
// INPUTS — TIME SESSION
// =====================================================

input bool UseSessionFilter = true;
input int  StartHour        = 8;
input int  StartMinute      = 30;
input int  EndHour          = 17;
input int  EndMinute        = 30;


// =====================================================
// INPUTS — SPREAD FILTER
// =====================================================

input bool UseSpreadFilter = true;
input int  MaxSpreadPoints = 50;


// =====================================================
// INPUTS — TEMPORAL BOOST (e.g. NY 14:30 fade window)
// =====================================================

input bool UseTemporalBoost       = false;
input int  TemporalBoostHour      = 14;
input int  TemporalBoostMinute    = 30;
input int  TemporalBoostMinutes   = 60;
input double TemporalScoreReduction = 1.0;


// =====================================================
// INPUTS — SCORE ENGINE
// =====================================================

input double MinimumScoreToTrade = 5.0;

input int    RSIPeriod      = 14;
input double SellRSILevel   = 68.0;
input double BuyRSILevel    = 32.0;

input int    MomentumPeriod          = 14;
input double MomentumOverboughtLevel = 100.50;
input double MomentumOversoldLevel   = 99.50;

input int    ATRPeriod            = 14;
input int    ImpulseBars          = 3;
input double ImpulseATRMultiplier = 0.90;

input int    MeanMAPeriod            = 20;
input double MinDistanceFromMeanPips = 80;

input double SlowdownRangeFactor = 0.80;
input double WickBodyRatio       = 1.20;

input bool   UseLevelScore       = true;
input double NearLevelPips       = 80;
input double RoundLevelStepPips  = 1000;


// =====================================================
// INPUTS — SCORE WEIGHTS
// =====================================================

input double WeightRSI            = 1.0;
input double WeightMomentum       = 1.0;
input double WeightMomentumSlope  = 0.5;
input double WeightImpulse        = 1.5;
input double WeightMeanDistance   = 1.5;
input double WeightSlowdown       = 1.0;
input double WeightRejection      = 1.2;
input double WeightLevel          = 0.8;
input double WeightRSIDivergence  = 1.0;


// =====================================================
// INPUTS — TREND FILTER
// =====================================================

input bool     UseTrendFilter   = false;
input ENUM_TIMEFRAMES TrendFilterTF = PERIOD_H1;
input int      TrendEMAPeriod   = 200;
// 0 = sell only above EMA / buy only below (fade extension in trend)
// 1 = opposite (counter-trend only)
input int      TrendFilterMode  = 0;


// =====================================================
// INPUTS — RSI DIVERGENCE
// =====================================================

input bool   UseRSIDivergenceScore    = true;
input bool   RequireRSIDivergenceForEntry = false;
input int    DivergenceLookbackBars   = 100;
input double StrongRSIDivergenceDiff  = 3.0;
input double StrongDivergenceMinPips  = 10.0;


// =====================================================
// INPUTS — PROTECTION
// =====================================================

input bool UsePositionCloseTime     = false;
input int  PositionCloseTimeMinutes = 74;

input bool   UseNegativeTimeClose   = true;
input int    NegativeCloseMinutes   = 35;
input double MinNegativePipsToClose = 80;

input bool   UseBreakEvenProtection = true;
input bool   UseBreakEvenMoveSL     = true;
input bool   UseBreakEvenMarketClose = false;
input double BreakEvenTriggerPips   = 25;
input double BreakEvenSLBufferPips  = 2;
input double BreakEvenClosePips     = 3;
input double BreakEvenMaxLossPips   = 10;

input bool   UseBasketProfitClose = true;
input double BasketProfitMoney    = 25.0;

input bool   UseDailyProfitStop     = true;
input double DailyProfitTargetMoney = 40.0;

input bool   UseDailyLossStop     = true;
input double DailyLossLimitMoney  = 25.0;

input bool UseConsecutiveLossStop = true;
input int  MaxConsecutiveLosses   = 2;


// =====================================================
// INCLUDES (after inputs — shared with .mqh modules)
// =====================================================

#include "Gala_Constants.mqh"
#include "Gala_Core.mqh"
#include "Gala_Filters.mqh"
#include "Gala_State.mqh"
#include "Gala_Protection.mqh"
#include "Gala_Signal.mqh"


// =====================================================
// GLOBALS
// =====================================================

datetime g_lastBarTime     = 0;
int      g_lastLogDayKey   = -1;
string   g_lastLogReason   = "";


//+------------------------------------------------------------------+
int OnInit()
{
   if(!GalaValidateInputs())
      return(INIT_PARAMETERS_INCORRECT);

   GalaResetDailyState();
   GalaInitBestPipsCache();

   Print(GALA002_NAME, " v", GALA002_VERSION, " initialized on ", Symbol(),
         " magic=", GALA002_MAGIC);

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Comment("");
   Print(GALA002_NAME, " removed.");
}

//+------------------------------------------------------------------+
void OnTick()
{
   GalaManageProtection();

   if(TradeOnlyGoldSymbols && !GalaIsGoldSymbol())
      return;

   if(Bars < 300)
      return;

   if(UseNewBarOnly)
   {
      if(Time[0] == g_lastBarTime)
         return;

      g_lastBarTime = Time[0];
      GalaInvalidateDailyState();
   }

   string blockReason = "";

   if(!GalaCanOpenNewTrade(blockReason))
   {
      GalaLogBlockOnce(blockReason);
      return;
   }

   double buyScore  = 0;
   double sellScore = 0;
   int signal = GalaGetSignal(buyScore, sellScore);

   if(signal == 0)
      return;

   if(signal == 1 && !GalaDirectionAllowed(OP_BUY))
      return;

   if(signal == -1 && !GalaDirectionAllowed(OP_SELL))
      return;

   string tag = (signal == 1) ? "BUY" : "SELL";
   int ticket = -1;

   if(GalaOpenMarket((signal == 1) ? OP_BUY : OP_SELL, LotSize, StopLossPips, TakeProfitPips, tag, ticket))
      GalaInvalidateDailyState();

   GalaUpdateChartComment(buyScore, sellScore, blockReason);
}

//+------------------------------------------------------------------+
bool NeutralZoneSanityCheck()
{
   if(RSIPeriod < 2)
   {
      Print(GALA002_NAME, ": RSIPeriod must be >= 2");
      return false;
   }

   if(ImpulseBars < 1)
   {
      Print(GALA002_NAME, ": ImpulseBars must be >= 1");
      return false;
   }

   if(SellRSILevel <= BuyRSILevel)
   {
      Print(GALA002_NAME, ": SellRSILevel must be > BuyRSILevel");
      return false;
   }

   if(MinimumScoreToTrade <= 0)
   {
      Print(GALA002_NAME, ": MinimumScoreToTrade must be > 0");
      return false;
   }

   if(StartHour < 0 || StartHour > 23 || EndHour < 0 || EndHour > 23)
   {
      Print(GALA002_NAME, ": invalid session hours");
      return false;
   }

   return true;
}

//+------------------------------------------------------------------+
bool GalaDirectionAllowed(int orderType)
{
   GalaRefreshDailyState();

   if(orderType == OP_BUY && g_galaDaily.openBuys >= MaxSameDirectionOpen)
      return false;

   if(orderType == OP_SELL && g_galaDaily.openSells >= MaxSameDirectionOpen)
      return false;

   if(g_galaDaily.openCount >= MaxOpenTradesTotal)
      return false;

   return true;
}

//+------------------------------------------------------------------+
void GalaLogBlockOnce(string reason)
{
   if(reason == "" || reason == "SPREAD")
      return;

   int dayKey = GalaDateKey(TimeCurrent());

   if(g_lastLogDayKey == dayKey && g_lastLogReason == reason)
      return;

   g_lastLogDayKey = dayKey;
   g_lastLogReason = reason;

   if(DebugMode)
      Print(GALA002_NAME, ": entries blocked — ", reason);
}

//+------------------------------------------------------------------+
void GalaUpdateChartComment(double buyScore, double sellScore, string blockReason)
{
   if(!DebugMode)
      return;

   GalaRefreshDailyState();

   string text = StringFormat(
      "%s v%s\nBuy=%.2f Sell=%.2f\nOpen=%d Today=%d P/L=%.2f\nBlock=%s",
      GALA002_NAME,
      GALA002_VERSION,
      buyScore,
      sellScore,
      g_galaDaily.openCount,
      g_galaDaily.todayTrades,
      g_galaDaily.todayProfit,
      blockReason
   );

   Comment(text);
}

//+------------------------------------------------------------------+

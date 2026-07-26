//+------------------------------------------------------------------+
//| Gala002_standalone.mq4 — single-file copy/paste version           |
//| Gala002 v2.0.0 | Magic 700802 | Gold exhaustion EA               |
//| Paste into MetaEditor -> Save as Gala002.mq4 -> Compile (F7)     |
//+------------------------------------------------------------------+
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





// =====================================================
// INLINED MODULES (from .mqh)
// =====================================================

//+------------------------------------------------------------------+
//| Gala_Constants.mqh — shared identifiers for Gala002               |
//+------------------------------------------------------------------+

#define GALA002_NAME        "Gala002"
#define GALA002_MAGIC       700802
#define GALA002_SLIPPAGE    3
#define GALA002_VERSION     "2.0.0"

//+------------------------------------------------------------------+
//| Gala_Core.mqh — pips, lots, stops, open/close helpers             |
//+------------------------------------------------------------------+


//+------------------------------------------------------------------+
double GalaPipValue()
{
   if(Digits == 3 || Digits == 5)
      return Point * 10;

   return Point;
}

//+------------------------------------------------------------------+
double GalaNormalizeLots(double lots)
{
   double minLot  = MarketInfo(Symbol(), MODE_MINLOT);
   double maxLot  = MarketInfo(Symbol(), MODE_MAXLOT);
   double lotStep = MarketInfo(Symbol(), MODE_LOTSTEP);

   if(lots < minLot)
      lots = minLot;

   if(lots > maxLot)
      lots = maxLot;

   if(lotStep > 0)
      lots = MathFloor(lots / lotStep) * lotStep;

   return NormalizeDouble(lots, 2);
}

//+------------------------------------------------------------------+
double GalaMinStopDistance()
{
   int stopLevel = (int)MarketInfo(Symbol(), MODE_STOPLEVEL);

   if(stopLevel < 1)
      stopLevel = 1;

   return stopLevel * Point;
}

//+------------------------------------------------------------------+
void GalaNormalizeStops(int orderType, double openPrice, double &sl, double &tp)
{
   double minDist = GalaMinStopDistance();

   if(orderType == OP_BUY)
   {
      if(sl > 0 && openPrice - sl < minDist)
         sl = openPrice - minDist;

      if(tp > 0 && tp - openPrice < minDist)
         tp = openPrice + minDist;
   }

   if(orderType == OP_SELL)
   {
      if(sl > 0 && sl - openPrice < minDist)
         sl = openPrice + minDist;

      if(tp > 0 && openPrice - tp < minDist)
         tp = openPrice - minDist;
   }

   sl = NormalizeDouble(sl, Digits);
   tp = NormalizeDouble(tp, Digits);
}

//+------------------------------------------------------------------+
bool GalaIsOurOrder()
{
   if(OrderSymbol() != Symbol())
      return false;

   if(OrderMagicNumber() != GALA002_MAGIC)
      return false;

   if(OrderType() != OP_BUY && OrderType() != OP_SELL)
      return false;

   return true;
}

//+------------------------------------------------------------------+
double GalaOrderCurrentPips()
{
   double pip = GalaPipValue();

   if(OrderType() == OP_BUY)
      return (Bid - OrderOpenPrice()) / pip;

   if(OrderType() == OP_SELL)
      return (OrderOpenPrice() - Ask) / pip;

   return 0;
}

//+------------------------------------------------------------------+
bool GalaTradeEnvironmentOK()
{
   if(!IsTradeAllowed())
      return false;

   if(IsTradeContextBusy())
      return false;

   if(!IsConnected())
      return false;

   return true;
}

//+------------------------------------------------------------------+
bool GalaOpenMarket(int orderType, double lots, double slPips, double tpPips, string tag, int &ticketOut)
{
   ticketOut = -1;

   if(!GalaTradeEnvironmentOK())
      return false;

   RefreshRates();

   lots = GalaNormalizeLots(lots);

   if(lots <= 0)
   {
      if(DebugMode)
         Print(GALA002_NAME, ": invalid lot size.");

      return false;
   }

   double pip = GalaPipValue();
   double price = 0;
   double sl = 0;
   double tp = 0;

   if(orderType == OP_BUY)
   {
      price = Ask;

      if(slPips > 0)
         sl = price - slPips * pip;

      if(tpPips > 0)
         tp = price + tpPips * pip;
   }

   if(orderType == OP_SELL)
   {
      price = Bid;

      if(slPips > 0)
         sl = price + slPips * pip;

      if(tpPips > 0)
         tp = price - tpPips * pip;
   }

   price = NormalizeDouble(price, Digits);
   GalaNormalizeStops(orderType, price, sl, tp);

   string comment = GALA002_NAME + "_" + tag + "_v" + GALA002_VERSION;

   int ticket = OrderSend(
      Symbol(),
      orderType,
      lots,
      price,
      GALA002_SLIPPAGE,
      sl,
      tp,
      comment,
      GALA002_MAGIC,
      0,
      clrNONE
   );

   if(ticket < 0)
   {
      int err = GetLastError();

      Print(GALA002_NAME, " OrderSend failed. Error ", err, ": ", GalaErrorText(err));
      ResetLastError();
      return false;
   }

   ticketOut = ticket;

   Print(
      comment,
      " opened. Ticket=",
      ticket,
      " Lots=",
      DoubleToString(lots, 2),
      " Price=",
      DoubleToString(price, Digits)
   );

   return true;
}

//+------------------------------------------------------------------+
bool GalaCloseSelected(const string reason)
{
   if(!GalaTradeEnvironmentOK())
      return false;

   RefreshRates();

   int ticket = OrderTicket();
   int type   = OrderType();
   double lots = OrderLots();
   double closePrice = 0;

   if(type == OP_BUY)
      closePrice = Bid;

   if(type == OP_SELL)
      closePrice = Ask;

   closePrice = NormalizeDouble(closePrice, Digits);

   bool closed = OrderClose(ticket, lots, closePrice, GALA002_SLIPPAGE, clrNONE);

   if(!closed)
   {
      int err = GetLastError();

      Print(
         GALA002_NAME,
         " OrderClose failed. Ticket=",
         ticket,
         " Reason=",
         reason,
         " Error ",
         err,
         ": ",
         GalaErrorText(err)
      );

      ResetLastError();
      return false;
   }

   Print(GALA002_NAME, " closed. Ticket=", ticket, " Reason=", reason);
   return true;
}

//+------------------------------------------------------------------+
bool GalaModifyStopLoss(double newSL)
{
   if(!GalaTradeEnvironmentOK())
      return false;

   int ticket = OrderTicket();
   newSL = NormalizeDouble(newSL, Digits);

   bool ok = OrderModify(ticket, OrderOpenPrice(), newSL, OrderTakeProfit(), 0, clrNONE);

   if(!ok)
   {
      int err = GetLastError();

      if(DebugMode)
         Print(GALA002_NAME, " OrderModify failed. Ticket=", ticket, " Error ", err);

      ResetLastError();
   }

   return ok;
}

//+------------------------------------------------------------------+
string GalaErrorText(int errorCode)
{
   switch(errorCode)
   {
      case 0:    return "No error";
      case 1:    return "No error returned";
      case 2:    return "Common error";
      case 3:    return "Invalid trade parameters";
      case 4:    return "Trade server busy";
      case 5:    return "Old terminal version";
      case 6:    return "No connection with trade server";
      case 7:    return "Not enough rights";
      case 8:    return "Too frequent requests";
      case 9:    return "Malfunctional trade operation";
      case 64:   return "Account disabled";
      case 65:   return "Invalid account";
      case 128:  return "Trade timeout";
      case 129:  return "Invalid price";
      case 130:  return "Invalid stops";
      case 131:  return "Invalid trade volume";
      case 132:  return "Market closed";
      case 133:  return "Trade disabled";
      case 134:  return "Not enough money";
      case 135:  return "Price changed";
      case 136:  return "Off quotes";
      case 137:  return "Broker busy";
      case 138:  return "Requote";
      case 139:  return "Order locked";
      case 140:  return "Long positions only allowed";
      case 141:  return "Too many requests";
      case 145:  return "Modification denied";
      case 146:  return "Trade context busy";
      case 147:  return "Expiration denied by broker";
      case 148:  return "Too many orders";
      default:   return "Unknown error";
   }
}

//+------------------------------------------------------------------+
//| Gala_Filters.mqh — symbol, session, spread filters              |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
bool GalaIsGoldSymbol()
{
   string s = Symbol();

   if(StringFind(s, "XAU", 0) >= 0)
      return true;

   if(StringFind(s, "GOLD", 0) >= 0)
      return true;

   if(StringFind(s, "Gold", 0) >= 0)
      return true;

   if(StringFind(s, "gold", 0) >= 0)
      return true;

   return false;
}

//+------------------------------------------------------------------+
bool GalaIsSessionAllowed()
{
   datetime now = TimeCurrent();

   int currentMinutes = TimeHour(now) * 60 + TimeMinute(now);
   int startMinutes   = StartHour * 60 + StartMinute;
   int endMinutes     = EndHour * 60 + EndMinute;

   return (currentMinutes >= startMinutes && currentMinutes <= endMinutes);
}

//+------------------------------------------------------------------+
bool GalaIsSpreadAllowed(bool &logBlock)
{
   logBlock = false;

   int spread = (int)MarketInfo(Symbol(), MODE_SPREAD);

   if(spread <= MaxSpreadPoints)
      return true;

   logBlock = true;
   return false;
}

//+------------------------------------------------------------------+
bool GalaIsTemporalBoostWindow()
{
   if(!UseTemporalBoost)
      return false;

   datetime now = TimeCurrent();
   int currentMinutes = TimeHour(now) * 60 + TimeMinute(now);
   int boostStart = TemporalBoostHour * 60 + TemporalBoostMinute;
   int boostEnd   = boostStart + TemporalBoostMinutes;

   return (currentMinutes >= boostStart && currentMinutes <= boostEnd);
}

//+------------------------------------------------------------------+
//| Gala_State.mqh — daily statistics (single history pass)           |
//+------------------------------------------------------------------+

struct GalaDailyState
{
   int      todayKey;
   int      openCount;
   int      todayTrades;
   int      openBuys;
   int      openSells;
   double   todayProfit;
   int      consecutiveLosses;
   datetime lastOpenTime;
   bool     valid;
};

GalaDailyState g_galaDaily;

//+------------------------------------------------------------------+
int GalaDateKey(datetime t)
{
   return TimeYear(t) * 1000 + TimeDayOfYear(t);
}

//+------------------------------------------------------------------+
void GalaResetDailyState()
{
   g_galaDaily.todayKey          = 0;
   g_galaDaily.openCount         = 0;
   g_galaDaily.todayTrades       = 0;
   g_galaDaily.openBuys          = 0;
   g_galaDaily.openSells         = 0;
   g_galaDaily.todayProfit       = 0;
   g_galaDaily.consecutiveLosses = 0;
   g_galaDaily.lastOpenTime      = 0;
   g_galaDaily.valid             = false;
}

//+------------------------------------------------------------------+
void GalaRefreshDailyState()
{
   int todayKey = GalaDateKey(TimeCurrent());

   if(g_galaDaily.valid && g_galaDaily.todayKey == todayKey)
      return;

   g_galaDaily.todayKey          = todayKey;
   g_galaDaily.openCount         = 0;
   g_galaDaily.todayTrades       = 0;
   g_galaDaily.openBuys          = 0;
   g_galaDaily.openSells         = 0;
   g_galaDaily.todayProfit       = 0;
   g_galaDaily.consecutiveLosses = 0;
   g_galaDaily.lastOpenTime      = 0;

   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         continue;

      if(!GalaIsOurOrder())
         continue;

      g_galaDaily.openCount++;

      if(OrderType() == OP_BUY)
         g_galaDaily.openBuys++;
      else
         g_galaDaily.openSells++;

      if(GalaDateKey(OrderOpenTime()) == todayKey)
      {
         g_galaDaily.todayTrades++;

         if(OrderOpenTime() > g_galaDaily.lastOpenTime)
            g_galaDaily.lastOpenTime = OrderOpenTime();
      }

      g_galaDaily.todayProfit += OrderProfit() + OrderSwap() + OrderCommission();
   }

   bool countingConsecutive = true;

   for(int j = OrdersHistoryTotal() - 1; j >= 0; j--)
   {
      if(!OrderSelect(j, SELECT_BY_POS, MODE_HISTORY))
         continue;

      if(OrderSymbol() != Symbol())
         continue;

      if(OrderMagicNumber() != GALA002_MAGIC)
         continue;

      if(OrderType() != OP_BUY && OrderType() != OP_SELL)
         continue;

      if(GalaDateKey(OrderOpenTime()) == todayKey)
         g_galaDaily.todayTrades++;

      if(OrderOpenTime() > g_galaDaily.lastOpenTime)
         g_galaDaily.lastOpenTime = OrderOpenTime();

      if(GalaDateKey(OrderCloseTime()) == todayKey)
      {
         double pl = OrderProfit() + OrderSwap() + OrderCommission();
         g_galaDaily.todayProfit += pl;

         if(countingConsecutive)
         {
            if(pl < 0)
               g_galaDaily.consecutiveLosses++;
            else
               countingConsecutive = false;
         }
      }
   }

   g_galaDaily.valid = true;
}

//+------------------------------------------------------------------+
void GalaInvalidateDailyState()
{
   g_galaDaily.valid = false;
}

//+------------------------------------------------------------------+
bool GalaCanOpenNewTrade(string &blockReason)
{
   blockReason = "";

   GalaRefreshDailyState();

   if(UseSessionFilter && !GalaIsSessionAllowed())
   {
      blockReason = "SESSION";
      return false;
   }

   bool spreadLog = false;

   if(UseSpreadFilter && !GalaIsSpreadAllowed(spreadLog))
   {
      blockReason = "SPREAD";
      return false;
   }

   if(g_galaDaily.openCount >= MaxOpenTradesTotal)
   {
      blockReason = "MAX_OPEN";
      return false;
   }

   if(g_galaDaily.todayTrades >= MaxTradesPerDay)
   {
      blockReason = "MAX_DAY";
      return false;
   }

   if(g_galaDaily.lastOpenTime > 0)
   {
      int minutesPassed = (int)((TimeCurrent() - g_galaDaily.lastOpenTime) / 60);

      if(minutesPassed < MinMinutesBetweenTrades)
      {
         blockReason = "MIN_GAP";
         return false;
      }
   }

   if(UseDailyProfitStop && g_galaDaily.todayProfit >= DailyProfitTargetMoney)
   {
      blockReason = "DAILY_PROFIT";
      return false;
   }

   if(UseDailyLossStop && g_galaDaily.todayProfit <= -DailyLossLimitMoney)
   {
      blockReason = "DAILY_LOSS";
      return false;
   }

   if(UseConsecutiveLossStop && g_galaDaily.consecutiveLosses >= MaxConsecutiveLosses)
   {
      blockReason = "CONSEC_LOSS";
      return false;
   }

   return true;
}

//+------------------------------------------------------------------+
//| Gala_Protection.mqh — single-loop protection manager              |
//+------------------------------------------------------------------+

#define GALA_BEST_CACHE 32

int    g_bestTickets[GALA_BEST_CACHE];
double g_bestPips[GALA_BEST_CACHE];

//+------------------------------------------------------------------+
void GalaInitBestPipsCache()
{
   for(int i = 0; i < GALA_BEST_CACHE; i++)
   {
      g_bestTickets[i] = -1;
      g_bestPips[i]    = 0;
   }
}

//+------------------------------------------------------------------+
int GalaFindBestCacheIndex(int ticket)
{
   for(int i = 0; i < GALA_BEST_CACHE; i++)
   {
      if(g_bestTickets[i] == ticket)
         return i;
   }

   return -1;
}

//+------------------------------------------------------------------+
int GalaAllocateBestCacheIndex(int ticket)
{
   int idx = GalaFindBestCacheIndex(ticket);

   if(idx >= 0)
      return idx;

   for(int i = 0; i < GALA_BEST_CACHE; i++)
   {
      if(g_bestTickets[i] < 0)
      {
         g_bestTickets[i] = ticket;
         g_bestPips[i]    = 0;
         return i;
      }
   }

   return 0;
}

//+------------------------------------------------------------------+
void GalaPruneBestCache()
{
   for(int i = 0; i < GALA_BEST_CACHE; i++)
   {
      if(g_bestTickets[i] < 0)
         continue;

      if(!OrderSelect(g_bestTickets[i], SELECT_BY_TICKET))
      {
         g_bestTickets[i] = -1;
         g_bestPips[i]    = 0;
      }
   }
}

//+------------------------------------------------------------------+
double GalaGetCachedBestPips(int ticket, double currentPips)
{
   int idx = GalaAllocateBestCacheIndex(ticket);

   if(currentPips > g_bestPips[idx])
      g_bestPips[idx] = currentPips;

   return g_bestPips[idx];
}

//+------------------------------------------------------------------+
bool GalaStopAlreadyAtBreakEven()
{
   double pip = GalaPipValue();
   double openPrice = OrderOpenPrice();
   double sl = OrderStopLoss();

   if(sl <= 0)
      return false;

   double beBand = BreakEvenSLBufferPips * pip;

   if(OrderType() == OP_BUY)
      return (sl >= openPrice - beBand);

   if(OrderType() == OP_SELL)
      return (sl <= openPrice + beBand);

   return false;
}

//+------------------------------------------------------------------+
void GalaTryMoveStopToBreakEven()
{
   double pip = GalaPipValue();
   double openPrice = OrderOpenPrice();
   double minDist = GalaMinStopDistance();
   double newSL = 0;

   if(OrderType() == OP_BUY)
   {
      newSL = openPrice + BreakEvenSLBufferPips * pip;

      if(Bid - newSL < minDist)
         newSL = Bid - minDist;
   }

   if(OrderType() == OP_SELL)
   {
      newSL = openPrice - BreakEvenSLBufferPips * pip;

      if(newSL - Ask < minDist)
         newSL = Ask + minDist;
   }

   newSL = NormalizeDouble(newSL, Digits);
   GalaModifyStopLoss(newSL);
}

//+------------------------------------------------------------------+
void GalaManageProtection()
{
   GalaPruneBestCache();

   double basketProfit = 0;
   bool   needBasketClose = false;

   if(UseBasketProfitClose)
   {
      for(int i = OrdersTotal() - 1; i >= 0; i--)
      {
         if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;

         if(!GalaIsOurOrder())
            continue;

         basketProfit += OrderProfit() + OrderSwap() + OrderCommission();
      }

      if(basketProfit >= BasketProfitMoney)
         needBasketClose = true;
   }

   datetime now = TimeCurrent();

   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         continue;

      if(!GalaIsOurOrder())
         continue;

      if(needBasketClose)
      {
         GalaCloseSelected("BASKET_PROFIT");
         continue;
      }

      int ticket = OrderTicket();
      int elapsed = (int)(now - OrderOpenTime());
      double currentPips = GalaOrderCurrentPips();
      double bestPips = GalaGetCachedBestPips(ticket, currentPips);

      if(UsePositionCloseTime)
      {
         int minutes = PositionCloseTimeMinutes;

         if(minutes < 1)
            minutes = 1;

         if(minutes > 999)
            minutes = 999;

         if(elapsed >= minutes * 60)
         {
            GalaCloseSelected("POSITION_TIME_CLOSE");
            continue;
         }
      }

      if(UseNegativeTimeClose)
      {
         if(elapsed >= NegativeCloseMinutes * 60 && currentPips <= -MinNegativePipsToClose)
         {
            GalaCloseSelected("NEGATIVE_TIME_CLOSE");
            continue;
         }
      }

      if(UseBreakEvenProtection && bestPips >= BreakEvenTriggerPips)
      {
         if(UseBreakEvenMoveSL && !GalaStopAlreadyAtBreakEven())
            GalaTryMoveStopToBreakEven();

         if(UseBreakEvenMarketClose)
         {
            if(currentPips <= BreakEvenClosePips && currentPips >= -BreakEvenMaxLossPips)
               GalaCloseSelected("BREAK_EVEN_PROTECTION");
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Gala_Signal.mqh — weighted exhaustion scoring for Gala002         |
//+------------------------------------------------------------------+

#define GALA_SWING_LR 2

//+------------------------------------------------------------------+
bool GalaIsCandleSlowdown()
{
   double range1 = High[1] - Low[1];
   double range2 = High[2] - Low[2];

   if(range1 <= 0 || range2 <= 0)
      return false;

   return (range1 <= range2 * SlowdownRangeFactor);
}

//+------------------------------------------------------------------+
bool GalaIsBearishRejectionCandle()
{
   double open1  = Open[1];
   double close1 = Close[1];
   double high1  = High[1];
   double low1   = Low[1];

   double body = MathAbs(close1 - open1);
   double upperWick = high1 - MathMax(open1, close1);
   double totalRange = high1 - low1;

   if(totalRange <= 0)
      return false;

   if(body <= 0)
      body = totalRange * 0.10;

   return (upperWick >= body * WickBodyRatio);
}

//+------------------------------------------------------------------+
bool GalaIsBullishRejectionCandle()
{
   double open1  = Open[1];
   double close1 = Close[1];
   double high1  = High[1];
   double low1   = Low[1];

   double body = MathAbs(close1 - open1);
   double lowerWick = MathMin(open1, close1) - low1;
   double totalRange = high1 - low1;

   if(totalRange <= 0)
      return false;

   if(body <= 0)
      body = totalRange * 0.10;

   return (lowerWick >= body * WickBodyRatio);
}

//+------------------------------------------------------------------+
bool GalaIsNearRoundLevel(double price)
{
   double pip = GalaPipValue();

   if(RoundLevelStepPips <= 0)
      return false;

   double step = RoundLevelStepPips * pip;

   if(step <= 0)
      return false;

   double nearest = MathRound(price / step) * step;
   double distancePips = MathAbs(price - nearest) / pip;

   return (distancePips <= NearLevelPips);
}

//+------------------------------------------------------------------+
bool GalaIsNearSellLevel(double price)
{
   double pip = GalaPipValue();

   double todayHigh = iHigh(NULL, PERIOD_D1, 0);
   double yesterdayHigh = iHigh(NULL, PERIOD_D1, 1);

   if(MathAbs(price - todayHigh) / pip <= NearLevelPips)
      return true;

   if(MathAbs(price - yesterdayHigh) / pip <= NearLevelPips)
      return true;

   return GalaIsNearRoundLevel(price);
}

//+------------------------------------------------------------------+
bool GalaIsNearBuyLevel(double price)
{
   double pip = GalaPipValue();

   double todayLow = iLow(NULL, PERIOD_D1, 0);
   double yesterdayLow = iLow(NULL, PERIOD_D1, 1);

   if(MathAbs(price - todayLow) / pip <= NearLevelPips)
      return true;

   if(MathAbs(price - yesterdayLow) / pip <= NearLevelPips)
      return true;

   return GalaIsNearRoundLevel(price);
}

//+------------------------------------------------------------------+
bool GalaIsSwingHigh(int shift)
{
   for(int i = 1; i <= GALA_SWING_LR; i++)
   {
      if(High[shift] <= High[shift - i])
         return false;

      if(High[shift] <= High[shift + i])
         return false;
   }

   return true;
}

//+------------------------------------------------------------------+
bool GalaIsSwingLow(int shift)
{
   for(int i = 1; i <= GALA_SWING_LR; i++)
   {
      if(Low[shift] >= Low[shift - i])
         return false;

      if(Low[shift] >= Low[shift + i])
         return false;
   }

   return true;
}

//+------------------------------------------------------------------+
int GalaFindSwingHigh(int startShift, int maxLookback)
{
   int maxShift = MathMin(maxLookback, Bars - GALA_SWING_LR - 2);

   for(int i = startShift; i <= maxShift; i++)
   {
      if(GalaIsSwingHigh(i))
         return i;
   }

   return -1;
}

//+------------------------------------------------------------------+
int GalaFindSwingLow(int startShift, int maxLookback)
{
   int maxShift = MathMin(maxLookback, Bars - GALA_SWING_LR - 2);

   for(int i = startShift; i <= maxShift; i++)
   {
      if(GalaIsSwingLow(i))
         return i;
   }

   return -1;
}

//+------------------------------------------------------------------+
bool GalaHasBearishRSIDivergence()
{
   int recentHigh = GalaFindSwingHigh(2, DivergenceLookbackBars);

   if(recentHigh < 0)
      return false;

   int olderHigh = GalaFindSwingHigh(recentHigh + GALA_SWING_LR + 1, DivergenceLookbackBars);

   if(olderHigh < 0)
      return false;

   double priceRecent = High[recentHigh];
   double priceOlder  = High[olderHigh];

   double rsiRecent = iRSI(NULL, 0, RSIPeriod, PRICE_CLOSE, recentHigh);
   double rsiOlder  = iRSI(NULL, 0, RSIPeriod, PRICE_CLOSE, olderHigh);

   double priceMovePips = MathAbs(priceRecent - priceOlder) / GalaPipValue();
   double rsiDiff       = rsiOlder - rsiRecent;

   return (priceRecent > priceOlder &&
           rsiRecent < rsiOlder &&
           rsiDiff >= StrongRSIDivergenceDiff &&
           priceMovePips >= StrongDivergenceMinPips);
}

//+------------------------------------------------------------------+
bool GalaHasBullishRSIDivergence()
{
   int recentLow = GalaFindSwingLow(2, DivergenceLookbackBars);

   if(recentLow < 0)
      return false;

   int olderLow = GalaFindSwingLow(recentLow + GALA_SWING_LR + 1, DivergenceLookbackBars);

   if(olderLow < 0)
      return false;

   double priceRecent = Low[recentLow];
   double priceOlder  = Low[olderLow];

   double rsiRecent = iRSI(NULL, 0, RSIPeriod, PRICE_CLOSE, recentLow);
   double rsiOlder  = iRSI(NULL, 0, RSIPeriod, PRICE_CLOSE, olderLow);

   double priceMovePips = MathAbs(priceRecent - priceOlder) / GalaPipValue();
   double rsiDiff       = rsiRecent - rsiOlder;

   return (priceRecent < priceOlder &&
           rsiRecent > rsiOlder &&
           rsiDiff >= StrongRSIDivergenceDiff &&
           priceMovePips >= StrongDivergenceMinPips);
}

//+------------------------------------------------------------------+
bool GalaTrendAllowsSell(double close1)
{
   if(!UseTrendFilter)
      return true;

   double trendEma = iMA(NULL, TrendFilterTF, TrendEMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 1);

   if(TrendFilterMode == 0)
      return (close1 > trendEma);

   return (close1 < trendEma);
}

//+------------------------------------------------------------------+
bool GalaTrendAllowsBuy(double close1)
{
   if(!UseTrendFilter)
      return true;

   double trendEma = iMA(NULL, TrendFilterTF, TrendEMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 1);

   if(TrendFilterMode == 0)
      return (close1 < trendEma);

   return (close1 > trendEma);
}

//+------------------------------------------------------------------+
int GalaGetSignal(double &buyScoreOut, double &sellScoreOut)
{
   buyScoreOut  = 0;
   sellScoreOut = 0;

   double close1 = Close[1];
   double rsi1 = iRSI(NULL, 0, RSIPeriod, PRICE_CLOSE, 1);
   double mom1 = iMomentum(NULL, 0, MomentumPeriod, PRICE_CLOSE, 1);
   double mom2 = iMomentum(NULL, 0, MomentumPeriod, PRICE_CLOSE, 2);
   double atr  = iATR(NULL, 0, ATRPeriod, 1);
   double ema  = iMA(NULL, 0, MeanMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 1);
   double pip  = GalaPipValue();

   double impulseMove = close1 - Close[ImpulseBars + 1];
   double impulseAbs  = MathAbs(impulseMove);

   bool upwardImpulse   = false;
   bool downwardImpulse = false;

   if(atr > 0)
   {
      if(impulseMove > 0 && impulseAbs >= atr * ImpulseATRMultiplier)
         upwardImpulse = true;

      if(impulseMove < 0 && impulseAbs >= atr * ImpulseATRMultiplier)
         downwardImpulse = true;
   }

   double distanceFromMeanPips = MathAbs(close1 - ema) / pip;
   bool priceAboveMeanFar = close1 > ema && distanceFromMeanPips >= MinDistanceFromMeanPips;
   bool priceBelowMeanFar = close1 < ema && distanceFromMeanPips >= MinDistanceFromMeanPips;

   bool candleSlowdown = GalaIsCandleSlowdown();
   bool sellRejection  = GalaIsBearishRejectionCandle();
   bool buyRejection   = GalaIsBullishRejectionCandle();

   bool sellNearLevel = false;
   bool buyNearLevel  = false;

   if(UseLevelScore)
   {
      sellNearLevel = GalaIsNearSellLevel(close1);
      buyNearLevel  = GalaIsNearBuyLevel(close1);
   }

   bool bearDiv = false;
   bool bullDiv = false;

   if(UseRSIDivergenceScore || RequireRSIDivergenceForEntry)
   {
      bearDiv = GalaHasBearishRSIDivergence();
      bullDiv = GalaHasBullishRSIDivergence();
   }

   double minScore = MinimumScoreToTrade;

   if(GalaIsTemporalBoostWindow())
      minScore -= TemporalScoreReduction;

   if(minScore < 1.0)
      minScore = 1.0;

   // ---- SELL score ----
   if(rsi1 >= SellRSILevel)
      sellScoreOut += WeightRSI;

   if(mom1 >= MomentumOverboughtLevel)
      sellScoreOut += WeightMomentum;

   if(mom1 < mom2)
      sellScoreOut += WeightMomentumSlope;

   if(upwardImpulse)
      sellScoreOut += WeightImpulse;

   if(priceAboveMeanFar)
      sellScoreOut += WeightMeanDistance;

   if(candleSlowdown && upwardImpulse)
      sellScoreOut += WeightSlowdown;

   if(sellRejection)
      sellScoreOut += WeightRejection;

   if(sellNearLevel)
      sellScoreOut += WeightLevel;

   if(UseRSIDivergenceScore && bearDiv)
      sellScoreOut += WeightRSIDivergence;

   // ---- BUY score ----
   if(rsi1 <= BuyRSILevel)
      buyScoreOut += WeightRSI;

   if(mom1 <= MomentumOversoldLevel)
      buyScoreOut += WeightMomentum;

   if(mom1 > mom2)
      buyScoreOut += WeightMomentumSlope;

   if(downwardImpulse)
      buyScoreOut += WeightImpulse;

   if(priceBelowMeanFar)
      buyScoreOut += WeightMeanDistance;

   if(candleSlowdown && downwardImpulse)
      buyScoreOut += WeightSlowdown;

   if(buyRejection)
      buyScoreOut += WeightRejection;

   if(buyNearLevel)
      buyScoreOut += WeightLevel;

   if(UseRSIDivergenceScore && bullDiv)
      buyScoreOut += WeightRSIDivergence;

   if(RequireRSIDivergenceForEntry)
   {
      if(sellScoreOut >= minScore && !bearDiv)
         sellScoreOut = 0;

      if(buyScoreOut >= minScore && !bullDiv)
         buyScoreOut = 0;
   }

   if(!GalaTrendAllowsSell(close1))
      sellScoreOut = 0;

   if(!GalaTrendAllowsBuy(close1))
      buyScoreOut = 0;

   if(DebugMode)
   {
      Print(
         GALA002_NAME,
         " scores buy=",
         DoubleToString(buyScoreOut, 2),
         " sell=",
         DoubleToString(sellScoreOut, 2),
         " min=",
         DoubleToString(minScore, 2),
         " RSI=",
         DoubleToString(rsi1, 2)
      );
   }

   if(sellScoreOut >= minScore && sellScoreOut > buyScoreOut)
      return -1;

   if(buyScoreOut >= minScore && buyScoreOut > sellScoreOut)
      return 1;

   return 0;
}

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
bool GalaValidateInputs()
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
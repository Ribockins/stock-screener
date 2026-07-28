//+------------------------------------------------------------------+
//| Gala_State.mqh — daily statistics (single history pass)           |
//+------------------------------------------------------------------+
#ifndef GALA_STATE_MQH
#define GALA_STATE_MQH

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

#endif

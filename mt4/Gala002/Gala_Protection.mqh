//+------------------------------------------------------------------+
//| Gala_Protection.mqh — single-loop protection manager              |
//+------------------------------------------------------------------+
#ifndef GALA_PROTECTION_MQH
#define GALA_PROTECTION_MQH

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

#endif

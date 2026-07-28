//+------------------------------------------------------------------+
//| Gala_Filters.mqh — symbol, session, spread filters              |
//+------------------------------------------------------------------+
#ifndef GALA_FILTERS_MQH
#define GALA_FILTERS_MQH

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

#endif

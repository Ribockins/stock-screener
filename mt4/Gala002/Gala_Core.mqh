//+------------------------------------------------------------------+
//| Gala_Core.mqh — pips, lots, stops, open/close helpers             |
//+------------------------------------------------------------------+
#ifndef GALA_CORE_MQH
#define GALA_CORE_MQH

#include "Gala_Constants.mqh"

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

#endif

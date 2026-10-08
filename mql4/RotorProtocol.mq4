#property copyright "ROTOR protocol"
#property version   "1.00"
#property strict

/*
   Вход по одной линии V. Повторных индикаторов нет.

   V = среднее из тех членов, которые посчитались:
     структура = clip((close - SMA) / ATR)
     импульс   = clip((close - close[MomentumBars]) / ATR)
     объём     = clip((MFI - 50) / 50)
   Если объёма нет, объём из среднего выпадает, а не подставляется нулём.
   ATR — простое среднее истинного диапазона, не Wilder.
   Каждый член обрезается в [-1, +1].

   Считается только закрытый бар.
   Buy:  V пересекла +EntryLevel снизу вверх.
   Sell: V пересекла -EntryLevel сверху вниз.
   Одна позиция. Противоположный сигнал закрывает старую и открывает новую.
   Возврат V через ноль закрывает позицию и новым входом не является.
   Свечи, RSI, MACD, дивергенции и точки LIMES в приказ не входят.
*/

input bool   SendOrders              = false;
input double LotSize                 = 0.01;
input int    SlippagePoints          = 30;
input int    MagicNumber             = 20261008;
input int    SmaPeriod               = 20;
input int    AtrPeriod               = 14;
input int    MomentumBars            = 3;
input int    MfiPeriod               = 14;
input double EntryLevel              = 0.5;
input double StopAtr                 = 1.5;
input double TakeAtr                 = 2.0;
input int    MaxSpreadPoints         = 0;
input bool   ExitWhenPressureGone    = true;

datetime g_lastClosedBar = 0;

int OnInit()
{
   if(SmaPeriod < 1 || AtrPeriod < 1 || MomentumBars < 1 || MfiPeriod < 1)
      return INIT_PARAMETERS_INCORRECT;
   if(EntryLevel <= 0.0 || EntryLevel >= 1.0)
      return INIT_PARAMETERS_INCORRECT;
   g_lastClosedBar = Time[0];
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   Comment("");
   int i;
   for(i = ObjectsTotal() - 1; i >= 0; i--)
   {
      string name = ObjectName(i);
      if(StringFind(name, "ROTOR_") == 0)
         ObjectDelete(name);
   }
}

void OnTick()
{
   int need = SmaPeriod + AtrPeriod + MomentumBars + MfiPeriod + 5;
   if(Bars <= need)
      return;
   if(Time[0] == g_lastClosedBar)
      return;
   g_lastClosedBar = Time[0];

   double structureNow = 0.0;
   double momentumNow = 0.0;
   double volumeNow = 0.0;
   bool structureOk = false;
   bool momentumOk = false;
   bool volumeOk = false;
   double vNow = VectorAt(1, structureNow, momentumNow, volumeNow, structureOk, momentumOk, volumeOk);
   double ignoredA = 0.0;
   double ignoredB = 0.0;
   double ignoredC = 0.0;
   bool ignoredD = false;
   bool ignoredE = false;
   bool ignoredF = false;
   double vPrev = VectorAt(2, ignoredA, ignoredB, ignoredC, ignoredD, ignoredE, ignoredF);
   if(vNow == EMPTY_VALUE || vPrev == EMPTY_VALUE)
      return;

   int signal = CrossSignal(vPrev, vNow);
   Publish(vNow, vPrev, structureNow, momentumNow, volumeNow, structureOk, momentumOk, volumeOk, signal);
   if(signal != 0)
      MarkEntry(1, signal > 0);

   if(!SendOrders)
      return;
   if(!IsConnected() || !IsTradeAllowed())
      return;
   if(MaxSpreadPoints > 0 && SpreadPoints() > MaxSpreadPoints)
      return;

   int ticket = FindPosition();
   if(signal != 0 && ticket >= 0)
   {
      if(!OrderSelect(ticket, SELECT_BY_TICKET, MODE_TRADES))
         return;
      int held = OrderType();
      bool same = (signal > 0 && held == OP_BUY) || (signal < 0 && held == OP_SELL);
      if(same)
         return;
      if(!CloseTicket(ticket))
         return;
      ticket = -1;
   }

   if(signal == 0 && ExitWhenPressureGone && ticket >= 0)
   {
      if(!OrderSelect(ticket, SELECT_BY_TICKET, MODE_TRADES))
         return;
      int heldSide = OrderType();
      bool pressureGone = (heldSide == OP_BUY && vPrev >= 0.0 && vNow < 0.0) ||
                          (heldSide == OP_SELL && vPrev <= 0.0 && vNow > 0.0);
      if(pressureGone)
         CloseTicket(ticket);
      return;
   }

   if(signal > 0)
      OpenTrade(OP_BUY);
   else if(signal < 0)
      OpenTrade(OP_SELL);
}

double Clip(double value)
{
   if(value > 1.0)
      return 1.0;
   if(value < -1.0)
      return -1.0;
   return value;
}

double SmaAtr(int shift)
{
   if(shift < 0 || Bars <= shift + AtrPeriod + 1)
      return 0.0;
   double sum = 0.0;
   int i;
   for(i = 0; i < AtrPeriod; i++)
   {
      int bar = shift + i;
      double previousClose = Close[bar + 1];
      double range = High[bar] - Low[bar];
      double up = MathAbs(High[bar] - previousClose);
      double down = MathAbs(Low[bar] - previousClose);
      double tr = range;
      if(up > tr)
         tr = up;
      if(down > tr)
         tr = down;
      sum += tr;
   }
   return sum / AtrPeriod;
}

bool StructureAt(int shift, double &score)
{
   if(Bars <= shift + SmaPeriod || Bars <= shift + AtrPeriod + 1)
      return false;
   double atr = SmaAtr(shift);
   if(atr <= 0.0)
      return false;
   double sma = iMA(NULL, 0, SmaPeriod, 0, MODE_SMA, PRICE_CLOSE, shift);
   if(sma == EMPTY_VALUE)
      return false;
   score = Clip((Close[shift] - sma) / atr);
   return true;
}

bool MomentumAt(int shift, double &score)
{
   if(Bars <= shift + MomentumBars || Bars <= shift + AtrPeriod + 1)
      return false;
   double atr = SmaAtr(shift);
   if(atr <= 0.0)
      return false;
   score = Clip((Close[shift] - Close[shift + MomentumBars]) / atr);
   return true;
}

bool VolumeAt(int shift, double &score)
{
   if(Bars <= shift + MfiPeriod)
      return false;
   int i;
   bool anyVolume = false;
   for(i = 0; i < MfiPeriod; i++)
   {
      if(Volume[shift + i] > 0)
      {
         anyVolume = true;
         break;
      }
   }
   if(!anyVolume)
      return false;
   double mfi = iMFI(NULL, 0, MfiPeriod, shift);
   if(mfi == EMPTY_VALUE)
      return false;
   score = Clip((mfi - 50.0) / 50.0);
   return true;
}

double VectorAt(int shift, double &structure, double &momentum, double &volume,
                bool &structureOk, bool &momentumOk, bool &volumeOk)
{
   structureOk = StructureAt(shift, structure);
   momentumOk = MomentumAt(shift, momentum);
   volumeOk = VolumeAt(shift, volume);
   double sum = 0.0;
   int count = 0;
   if(structureOk)
   {
      sum += structure;
      count++;
   }
   if(momentumOk)
   {
      sum += momentum;
      count++;
   }
   if(volumeOk)
   {
      sum += volume;
      count++;
   }
   if(count == 0)
      return EMPTY_VALUE;
   return sum / count;
}

int CrossSignal(double previous, double current)
{
   if(previous <= EntryLevel && current > EntryLevel)
      return 1;
   if(previous >= -EntryLevel && current < -EntryLevel)
      return -1;
   return 0;
}

int SpreadPoints()
{
   double point = MarketInfo(Symbol(), MODE_POINT);
   if(point <= 0.0)
      return 0;
   return (int)MathRound((Ask - Bid) / point);
}

int FindPosition()
{
   int i;
   for(i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         continue;
      if(OrderSymbol() != Symbol() || OrderMagicNumber() != MagicNumber)
         continue;
      if(OrderType() == OP_BUY || OrderType() == OP_SELL)
         return OrderTicket();
   }
   return -1;
}

bool CloseTicket(int ticket)
{
   if(!OrderSelect(ticket, SELECT_BY_TICKET, MODE_TRADES))
      return false;
   RefreshRates();
   double price = (OrderType() == OP_BUY) ? Bid : Ask;
   bool closed = OrderClose(ticket, OrderLots(), price, SlippagePoints, clrNONE);
   if(!closed)
      Print("ROTOR close failed, ticket ", ticket, " error ", GetLastError());
   return closed;
}

double NormalizeLot(double lot)
{
   double minLot = MarketInfo(Symbol(), MODE_MINLOT);
   double maxLot = MarketInfo(Symbol(), MODE_MAXLOT);
   double step = MarketInfo(Symbol(), MODE_LOTSTEP);
   if(step <= 0.0)
      step = minLot;
   if(step <= 0.0)
      return lot;
   lot = MathFloor(lot / step + 1e-8) * step;
   if(lot < minLot)
      lot = minLot;
   if(maxLot > 0.0 && lot > maxLot)
      lot = maxLot;
   int digits = 0;
   double probe = step;
   while(digits < 8 && MathAbs(probe - MathRound(probe)) > 1e-8)
   {
      probe *= 10.0;
      digits++;
   }
   return NormalizeDouble(lot, digits);
}

bool StopDistanceOk(double atr)
{
   if(StopAtr <= 0.0 && TakeAtr <= 0.0)
      return true;
   double point = MarketInfo(Symbol(), MODE_POINT);
   if(point <= 0.0)
      return false;
   double minDist = MarketInfo(Symbol(), MODE_STOPLEVEL) * point;
   if(StopAtr > 0.0 && StopAtr * atr < minDist)
      return false;
   if(TakeAtr > 0.0 && TakeAtr * atr < minDist)
      return false;
   return true;
}

void OpenTrade(int side)
{
   double atr = SmaAtr(1);
   if(atr <= 0.0 || !StopDistanceOk(atr))
   {
      Print("ROTOR skip entry: ATR or broker stop distance");
      return;
   }
   RefreshRates();
   double lot = NormalizeLot(LotSize);
   double entry;
   double sl = 0.0;
   double tp = 0.0;
   color mark;
   if(side == OP_BUY)
   {
      entry = Ask;
      if(StopAtr > 0.0)
         sl = entry - StopAtr * atr;
      if(TakeAtr > 0.0)
         tp = entry + TakeAtr * atr;
      mark = clrGreen;
   }
   else
   {
      entry = Bid;
      if(StopAtr > 0.0)
         sl = entry + StopAtr * atr;
      if(TakeAtr > 0.0)
         tp = entry - TakeAtr * atr;
      mark = clrRed;
   }
   int digits = (int)MarketInfo(Symbol(), MODE_DIGITS);
   sl = (sl == 0.0) ? 0.0 : NormalizeDouble(sl, digits);
   tp = (tp == 0.0) ? 0.0 : NormalizeDouble(tp, digits);
   int ticket = OrderSend(Symbol(), side, lot, entry, SlippagePoints, sl, tp, "ROTOR V", MagicNumber, 0, mark);
   if(ticket < 0)
      Print("ROTOR entry failed, error ", GetLastError());
}

void MarkEntry(int shift, bool buy)
{
   string name = "ROTOR_" + DoubleToString((double)Time[shift], 0);
   if(ObjectFind(name) >= 0)
      return;
   double price = buy ? Low[shift] : High[shift];
   if(!ObjectCreate(name, OBJ_ARROW, 0, Time[shift], price))
      return;
   ObjectSet(name, OBJPROP_ARROWCODE, buy ? 233 : 234);
   ObjectSet(name, OBJPROP_COLOR, buy ? clrLime : clrTomato);
   ObjectSet(name, OBJPROP_WIDTH, 2);
}

void Publish(double vNow, double vPrev, double structure, double momentum, double volume,
             bool structureOk, bool momentumOk, bool volumeOk, int signal)
{
   string side = "нет";
   if(signal > 0)
      side = "BUY";
   else if(signal < 0)
      side = "SELL";
   string orders = SendOrders ? "заявки включены" : "заявки выключены, на графике только стрелка";
   Comment(
      "ROTOR V ", DoubleToString(vNow, 3),
      "  предыдущее ", DoubleToString(vPrev, 3),
      "\nструктура ", (structureOk ? DoubleToString(structure, 3) : "нет"),
      "  импульс ", (momentumOk ? DoubleToString(momentum, 3) : "нет"),
      "  объём ", (volumeOk ? DoubleToString(volume, 3) : "нет"),
      "\nвход: ", side,
      "\n", orders
   );
}

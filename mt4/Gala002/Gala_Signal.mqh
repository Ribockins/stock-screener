//+------------------------------------------------------------------+
//| Gala_Signal.mqh — weighted exhaustion scoring for Gala002         |
//+------------------------------------------------------------------+
#ifndef GALA_SIGNAL_MQH
#define GALA_SIGNAL_MQH

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

#endif

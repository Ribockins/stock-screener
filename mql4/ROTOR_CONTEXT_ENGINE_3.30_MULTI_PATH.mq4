//+------------------------------------------------------------------+
//|        ROTOR_CONTEXT_ENGINE_3.30_MULTI_PATH.mq4                  |
//|        Multi-Path Context / Setup / Trigger / Regime EA          |
//+------------------------------------------------------------------+
#property strict
#property version   "3.30"

enum TradeDirectionMode
{
   TradeBuyOnly  = 0,
   TradeSellOnly = 1,
   TradeBoth     = 2
};

enum DivergenceMode
{
   DivergenceAny       = 0,
   DivergenceBoth      = 1,
   DivergenceRSIOnly   = 2,
   DivergenceRotorOnly = 3
};

enum DirectionalSignalState
{
   DirectionalSignalIdle      = 0,
   DirectionalSignalArmed     = 1,
   DirectionalSignalTriggered = 2
};

enum ContextZone
{
   ContextZoneExtremeBuy    = 0,
   ContextZonePrimeBuy      = 1,
   ContextZoneSecondaryBuy  = 2,
   ContextZoneNeutral       = 3,
   ContextZoneSecondarySell = 4,
   ContextZonePrimeSell     = 5,
   ContextZoneExtremeSell    = 6
};

enum HigherTimeframeRegime
{
   HigherTimeframeRegimeAligned    = 0,
   HigherTimeframeRegimeRecovering = 1,
   HigherTimeframeRegimeNeutral    = 2,
   HigherTimeframeRegimeOpposed    = 3
};

enum RotorTriggerType
{
   RotorTriggerNone           = 0,
   RotorTriggerFreshCross     = 1,
   RotorTriggerContinuation   = 2,
   RotorTriggerReAcceleration = 3
};

enum DivergenceStrengthClass
{
   DivergenceStrengthWeak    = 0,
   DivergenceStrengthNormal  = 1,
   DivergenceStrengthStrong  = 2,
   DivergenceStrengthExtreme = 3
};

enum QualityRoute
{
   QualityRouteNone                    = 0,
   QualityRoutePrimeFreshCross         = 1,
   QualityRoutePrimeContinuation       = 2,
   QualityRouteSecondaryStrongReaction = 3,
   QualityRouteExtremeRecovery         = 4
};

struct MarketMapResult
{
   bool        isReady;
   double      contextOpenPrice;
   double      contextHighPrice;
   double      contextLowPrice;
   double      contextRangePrice;
   double      contextPositionFraction;
   double      contextAtrValue;
   double      contextMoveFromOpenInAtr;
   ContextZone currentContextZone;
};

struct DivergenceResult
{
   bool                    isDetected;
   bool                    hasRsiDivergence;
   bool                    hasRotorDivergence;
   int                     recentPivotShift;
   int                     previousPivotShift;
   double                  recentPivotPrice;
   double                  previousPivotPrice;
   double                  priceExtensionInAtr;
   double                  rsiDivergenceDelta;
   double                  rotorDivergenceDelta;
   double                  combinedStrengthScore;
   DivergenceStrengthClass strengthClass;
};

struct RotorTriggerResult
{
   bool             isDetected;
   RotorTriggerType triggerType;
   double           currentRotorValue;
   double           previousRotorValue;
   double           olderRotorValue;
   double           rotorVelocity;
   double           previousRotorVelocity;
   double           rotorAcceleration;
   double           triggerStrengthScore;
};

struct RegimeResult
{
   bool                  isReady;
   double                currentRotorValue;
   double                previousRotorValue;
   double                rotorSlope;
   HigherTimeframeRegime regimeState;
};

struct TradeGeometryResult
{
   bool   isReady;
   double entryPrice;
   double stopLossPrice;
   double takeProfitPrice;
   double stopLossDistancePoints;
   double takeProfitDistancePoints;
   double rewardRiskRatio;
   double roomToTargetInAtr;
   string rejectionReason;
};

struct DirectionSetupState
{
   DirectionalSignalState currentState;

   datetime setupCreatedTime;
   datetime triggerConfirmedTime;

   int setupAgeInBars;
   int triggerAgeInBars;

   double divergencePivotPrice;

   double setupContextPositionFraction;
   ContextZone setupContextZone;

   double setupRotorValue;
   double setupRegimeRotorValue;
   double setupRegimeRotorSlope;

   double divergenceStrengthScore;
   DivergenceStrengthClass divergenceStrengthClass;

   RotorTriggerType triggerType;
   double triggerStrengthScore;

   HigherTimeframeRegime currentRegimeState;
   QualityRoute selectedQualityRoute;

   bool primaryEntryAlreadyUsed;
   string currentBlockReason;
};

// ==================================================================
// INPUTS
// ==================================================================

input string Header_01_Timeframes = "=== TIMEFRAME ROLES ===";
input ENUM_TIMEFRAMES ContextTimeframe = PERIOD_D1;
input ENUM_TIMEFRAMES RegimeTimeframe  = PERIOD_H1;

input string Header_02_Rotor = "=== ROTOR V ENGINE ===";
input int    SMAPeriod       = 20;
input int    MomentumBars    = 5;
input int    MFIPeriod       = 14;
input int    SimpleATRPeriod = 14;
input double EntryLevel      = 0.35;

input string Header_03_Context = "=== CONTEXT RANGE ZONES ===";
input double ExtremeBuyZoneMaximumFraction    = 0.25;
input double PrimeBuyZoneMaximumFraction      = 0.35;
input double SecondaryBuyZoneMaximumFraction  = 0.45;
input double SecondarySellZoneMinimumFraction = 0.55;
input double PrimeSellZoneMinimumFraction     = 0.65;
input double ExtremeSellZoneMinimumFraction   = 0.75;
input int    ContextATRPeriod = 14;

input string Header_04_Divergence = "=== DIVERGENCE SETUP ===";
input int RSIPeriod = 14;
input int PivotLeft  = 2;
input int PivotRight = 2;
input int DivergenceSearchBars = 120;
input DivergenceMode RequiredDivergenceMode = DivergenceAny;
input double MinimumPricePivotDistanceATR = 0.05;
input double MinimumRSIDivergenceDelta     = 1.00;
input double MinimumRotorDivergenceDelta   = 0.03;
input double NormalDivergenceScoreMinimum  = 30.0;
input double StrongDivergenceScoreMinimum  = 55.0;
input double ExtremeDivergenceScoreMinimum = 80.0;
input int MaximumSetupLifetimeBars = 8;

input string Header_05_Trigger = "=== ROTOR TRIGGER ENGINE ===";
input int MaximumTriggerLifetimeBars = 3;
input double MinimumRotorContinuationVelocity   = 0.03;
input double MinimumRotorReAccelerationVelocity = 0.02;
input double MinimumRotorReAcceleration         = 0.02;

input string Header_06_Regime = "=== REGIME ENGINE ===";
input double MinimumHigherTimeframeRecoverySlope = 0.03;
input double HigherTimeframeNeutralBand = 0.10;

input string Header_07_Quality = "=== QUALITY ROUTER ===";
input bool   UseQualityScoreAsEntryVeto = false;
input double MinimumQualityScore = 60.0;

input string Header_08_Geometry = "=== TRADE GEOMETRY ===";
input double StopATRBufferMultiplier = 0.20;
input double BuySpatialTargetFraction  = 0.65;
input double SellSpatialTargetFraction = 0.35;
input bool   UseGeometryAsEntryVeto = false;
input double MinimumRewardRiskRatio   = 1.20;
input double MinimumRoomToTargetInAtr = 0.30;

input string Header_09_Filters = "=== EXECUTION FILTERS ===";
input int    MaximumSpreadPoints = 30;
input bool   UseMinimumATRFilter = true;
input double MinimumWorkingATRPoints = 30.0;
input bool   BlockSundayTrading = true;
input bool   UseFridayCutoff = true;
input int    FridayCutoffHour = 20;

input string Header_10_Trade = "=== TRADE ===";
input TradeDirectionMode AllowedTradeDirection = TradeBoth;
input double FixedLotSize = 0.01;
input int MagicNumber = 953330;
input int SlippagePoints = 30;
input int OrderSendRetries = 3;
input bool ShowStatusOnChart = true;

#define ROTOR_EPS 0.0000001

datetime g_lastSignalBarTime = 0;

double g_currentClosedRotorValue = 0.0;
double g_previousClosedRotorValue = 0.0;
double g_olderClosedRotorValue = 0.0;

bool g_currentRotorValueValid = false;
bool g_previousRotorValueValid = false;
bool g_olderRotorValueValid = false;

DirectionSetupState g_buySetupState;
DirectionSetupState g_sellSetupState;

MarketMapResult g_latestMarketMap;

string g_lastAction = "INIT";

// ==================================================================
// INITIALIZATION
// ==================================================================

int OnInit()
{
   if(!ValidateInputs())
      return(INIT_PARAMETERS_INCORRECT);

   InitializeDirectionState(g_buySetupState);
   InitializeDirectionState(g_sellSetupState);

   g_lastSignalBarTime = iTime(Symbol(), Period(), 0);

   LoadInitialRotorHistory();
   UpdateMarketMap();

   Print(
      "[ROTOR 3.30] Initialized",
      " | Symbol=", Symbol(),
      " | SignalTF=", TimeframeText(Period()),
      " | ContextTF=", TimeframeText((int)ContextTimeframe),
      " | RegimeTF=", TimeframeText((int)RegimeTimeframe)
   );

   g_lastAction = "INITIALIZED";
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   if(ShowStatusOnChart)
      Comment("");
}

void OnTick()
{
   bool isNewSignalBar = IsNewSignalBar();

   if(isNewSignalBar)
   {
      UpdateMarketMap();
      UpdateRotorHistory();

      AdvanceDirectionStateAge(OP_BUY);
      AdvanceDirectionStateAge(OP_SELL);

      DetectAndCreateOrRefreshSetup(OP_BUY);
      DetectAndCreateOrRefreshSetup(OP_SELL);

      DetectAndApplyTrigger(OP_BUY);
      DetectAndApplyTrigger(OP_SELL);

      if(CountOwnOpenPositions() == 0)
      {
         EvaluateTriggeredSetupAndTrade(OP_BUY);

         if(CountOwnOpenPositions() == 0)
            EvaluateTriggeredSetupAndTrade(OP_SELL);
      }
   }

   ManageTrade();

   if(ShowStatusOnChart)
      UpdateStatusPanel();
}

// ==================================================================
// VALIDATION
// ==================================================================

bool ValidateInputs()
{
   if(SMAPeriod < 1 || MomentumBars < 1 || MFIPeriod < 1 ||
      SimpleATRPeriod < 1 || ContextATRPeriod < 1 || RSIPeriod < 2)
      return(false);

   if(EntryLevel <= 0.0 || EntryLevel >= 1.0)
      return(false);

   if(ExtremeBuyZoneMaximumFraction <= 0.0 ||
      ExtremeBuyZoneMaximumFraction >= PrimeBuyZoneMaximumFraction ||
      PrimeBuyZoneMaximumFraction >= SecondaryBuyZoneMaximumFraction ||
      SecondaryBuyZoneMaximumFraction >= 0.50)
      return(false);

   if(SecondarySellZoneMinimumFraction <= 0.50 ||
      SecondarySellZoneMinimumFraction >= PrimeSellZoneMinimumFraction ||
      PrimeSellZoneMinimumFraction >= ExtremeSellZoneMinimumFraction ||
      ExtremeSellZoneMinimumFraction >= 1.0)
      return(false);

   if(PivotLeft < 1 || PivotRight < 1 || DivergenceSearchBars < 20)
      return(false);

   if(MinimumPricePivotDistanceATR < 0.0 ||
      MinimumRSIDivergenceDelta < 0.0 ||
      MinimumRotorDivergenceDelta < 0.0)
      return(false);

   if(NormalDivergenceScoreMinimum < 0.0 ||
      StrongDivergenceScoreMinimum <= NormalDivergenceScoreMinimum ||
      ExtremeDivergenceScoreMinimum <= StrongDivergenceScoreMinimum)
      return(false);

   if(MaximumSetupLifetimeBars < 1 || MaximumTriggerLifetimeBars < 1)
      return(false);

   if(MinimumRotorContinuationVelocity < 0.0 ||
      MinimumRotorReAccelerationVelocity < 0.0 ||
      MinimumRotorReAcceleration < 0.0)
      return(false);

   if(MinimumHigherTimeframeRecoverySlope < 0.0 ||
      HigherTimeframeNeutralBand < 0.0)
      return(false);

   if(StopATRBufferMultiplier < 0.0)
      return(false);

   if(BuySpatialTargetFraction <= 0.50 ||
      BuySpatialTargetFraction > 1.0 ||
      SellSpatialTargetFraction >= 0.50 ||
      SellSpatialTargetFraction < 0.0)
      return(false);

   if(MinimumRewardRiskRatio <= 0.0 ||
      MinimumRoomToTargetInAtr < 0.0)
      return(false);

   if(MaximumSpreadPoints < 0 ||
      MinimumWorkingATRPoints < 0.0)
      return(false);

   if(FixedLotSize <= 0.0 || MagicNumber <= 0 ||
      SlippagePoints < 0 || OrderSendRetries < 1)
      return(false);

   return(true);
}

// ==================================================================
// STATE HELPERS
// ==================================================================

void InitializeDirectionState(DirectionSetupState &directionState)
{
   directionState.currentState = DirectionalSignalIdle;
   directionState.setupCreatedTime = 0;
   directionState.triggerConfirmedTime = 0;
   directionState.setupAgeInBars = 0;
   directionState.triggerAgeInBars = 0;
   directionState.divergencePivotPrice = 0.0;
   directionState.setupContextPositionFraction = 0.0;
   directionState.setupContextZone = ContextZoneNeutral;
   directionState.setupRotorValue = 0.0;
   directionState.setupRegimeRotorValue = 0.0;
   directionState.setupRegimeRotorSlope = 0.0;
   directionState.divergenceStrengthScore = 0.0;
   directionState.divergenceStrengthClass = DivergenceStrengthWeak;
   directionState.triggerType = RotorTriggerNone;
   directionState.triggerStrengthScore = 0.0;
   directionState.currentRegimeState = HigherTimeframeRegimeNeutral;
   directionState.selectedQualityRoute = QualityRouteNone;
   directionState.primaryEntryAlreadyUsed = false;
   directionState.currentBlockReason = "";
}

void AdvanceDirectionStateAge(int direction)
{
   if(direction == OP_BUY)
   {
      if(g_buySetupState.currentState == DirectionalSignalArmed)
      {
         g_buySetupState.setupAgeInBars++;

         if(g_buySetupState.setupAgeInBars > MaximumSetupLifetimeBars)
            ResetDirectionState(OP_BUY, "BUY SETUP EXPIRED");
      }
      else
      if(g_buySetupState.currentState == DirectionalSignalTriggered)
      {
         g_buySetupState.triggerAgeInBars++;

         if(g_buySetupState.triggerAgeInBars > MaximumTriggerLifetimeBars)
            ResetDirectionState(OP_BUY, "BUY TRIGGER EXPIRED");
      }

      return;
   }

   if(direction == OP_SELL)
   {
      if(g_sellSetupState.currentState == DirectionalSignalArmed)
      {
         g_sellSetupState.setupAgeInBars++;

         if(g_sellSetupState.setupAgeInBars > MaximumSetupLifetimeBars)
            ResetDirectionState(OP_SELL, "SELL SETUP EXPIRED");
      }
      else
      if(g_sellSetupState.currentState == DirectionalSignalTriggered)
      {
         g_sellSetupState.triggerAgeInBars++;

         if(g_sellSetupState.triggerAgeInBars > MaximumTriggerLifetimeBars)
            ResetDirectionState(OP_SELL, "SELL TRIGGER EXPIRED");
      }
   }
}

void ResetDirectionState(int direction, string reason)
{
   if(direction == OP_BUY)
      InitializeDirectionState(g_buySetupState);
   else
   if(direction == OP_SELL)
      InitializeDirectionState(g_sellSetupState);

   if(StringLen(reason) > 0)
      g_lastAction = reason;
}

// ==================================================================
// TIME / TEXT
// ==================================================================

bool IsNewSignalBar()
{
   datetime currentSignalBarTime = iTime(Symbol(), Period(), 0);

   if(currentSignalBarTime <= 0)
      return(false);

   if(g_lastSignalBarTime == 0)
   {
      g_lastSignalBarTime = currentSignalBarTime;
      return(false);
   }

   if(currentSignalBarTime != g_lastSignalBarTime)
   {
      g_lastSignalBarTime = currentSignalBarTime;
      return(true);
   }

   return(false);
}

string TimeframeText(int timeframe)
{
   if(timeframe == PERIOD_M1)  return("M1");
   if(timeframe == PERIOD_M5)  return("M5");
   if(timeframe == PERIOD_M15) return("M15");
   if(timeframe == PERIOD_M30) return("M30");
   if(timeframe == PERIOD_H1)  return("H1");
   if(timeframe == PERIOD_H4)  return("H4");
   if(timeframe == PERIOD_D1)  return("D1");
   if(timeframe == PERIOD_W1)  return("W1");
   if(timeframe == PERIOD_MN1) return("MN1");
   return(IntegerToString(timeframe));
}

string DirectionText(int direction)
{
   if(direction == OP_BUY)  return("BUY");
   if(direction == OP_SELL) return("SELL");
   return("NONE");
}

string ContextZoneText(ContextZone contextZone)
{
   if(contextZone == ContextZoneExtremeBuy)    return("EXTREME BUY");
   if(contextZone == ContextZonePrimeBuy)      return("PRIME BUY");
   if(contextZone == ContextZoneSecondaryBuy)  return("SECONDARY BUY");
   if(contextZone == ContextZoneNeutral)       return("NEUTRAL");
   if(contextZone == ContextZoneSecondarySell) return("SECONDARY SELL");
   if(contextZone == ContextZonePrimeSell)     return("PRIME SELL");
   if(contextZone == ContextZoneExtremeSell)   return("EXTREME SELL");
   return("UNKNOWN");
}

string RegimeText(HigherTimeframeRegime regimeState)
{
   if(regimeState == HigherTimeframeRegimeAligned)    return("ALIGNED");
   if(regimeState == HigherTimeframeRegimeRecovering) return("RECOVERING");
   if(regimeState == HigherTimeframeRegimeNeutral)    return("NEUTRAL");
   if(regimeState == HigherTimeframeRegimeOpposed)    return("OPPOSED");
   return("UNKNOWN");
}

string TriggerTypeText(RotorTriggerType triggerType)
{
   if(triggerType == RotorTriggerFreshCross)      return("FRESH CROSS");
   if(triggerType == RotorTriggerContinuation)    return("CONTINUATION");
   if(triggerType == RotorTriggerReAcceleration)  return("RE-ACCELERATION");
   return("NONE");
}

string DivergenceStrengthText(DivergenceStrengthClass strengthClass)
{
   if(strengthClass == DivergenceStrengthWeak)    return("WEAK");
   if(strengthClass == DivergenceStrengthNormal)  return("NORMAL");
   if(strengthClass == DivergenceStrengthStrong)  return("STRONG");
   if(strengthClass == DivergenceStrengthExtreme) return("EXTREME");
   return("UNKNOWN");
}

string QualityRouteText(QualityRoute qualityRoute)
{
   if(qualityRoute == QualityRoutePrimeFreshCross)         return("PATH A");
   if(qualityRoute == QualityRoutePrimeContinuation)       return("PATH B");
   if(qualityRoute == QualityRouteSecondaryStrongReaction) return("PATH C");
   if(qualityRoute == QualityRouteExtremeRecovery)         return("PATH D");
   return("NONE");
}

// ==================================================================
// ROTOR CORE
// ==================================================================

double ClipToUnitRange(double value)
{
   if(value > 1.0)  return(1.0);
   if(value < -1.0) return(-1.0);
   return(value);
}

double CalculateTrueRangeAtShift(int timeframe, int shift)
{
   double highPrice = iHigh(Symbol(), timeframe, shift);
   double lowPrice  = iLow(Symbol(), timeframe, shift);

   if(highPrice <= 0.0 || lowPrice <= 0.0 || highPrice < lowPrice)
      return(0.0);

   double previousClosePrice = iClose(Symbol(), timeframe, shift + 1);

   if(previousClosePrice <= 0.0)
      return(highPrice - lowPrice);

   double directRange  = highPrice - lowPrice;
   double highGapRange = MathAbs(highPrice - previousClosePrice);
   double lowGapRange  = MathAbs(lowPrice  - previousClosePrice);

   return(MathMax(directRange, MathMax(highGapRange, lowGapRange)));
}

bool CalculateSimpleAverageTrueRange(
   int timeframe,
   int shift,
   int period,
   double &averageTrueRangeValue)
{
   int totalBars = iBars(Symbol(), timeframe);

   if(period < 1 || totalBars <= shift + period + 1)
      return(false);

   double trueRangeSum = 0.0;

   for(int barIndex = shift; barIndex < shift + period; barIndex++)
   {
      double trueRangeValue =
         CalculateTrueRangeAtShift(timeframe, barIndex);

      if(trueRangeValue <= 0.0)
         return(false);

      trueRangeSum += trueRangeValue;
   }

   averageTrueRangeValue = trueRangeSum / period;
   return(averageTrueRangeValue > 0.0);
}

bool CalculateSimpleMovingAverage(
   int timeframe,
   int shift,
   int period,
   double &movingAverageValue)
{
   int totalBars = iBars(Symbol(), timeframe);

   if(period < 1 || totalBars <= shift + period)
      return(false);

   double closePriceSum = 0.0;

   for(int barIndex = shift; barIndex < shift + period; barIndex++)
   {
      double closePrice = iClose(Symbol(), timeframe, barIndex);

      if(closePrice <= 0.0)
         return(false);

      closePriceSum += closePrice;
   }

   movingAverageValue = closePriceSum / period;
   return(true);
}

bool HasUsableVolumeDataForMoneyFlowIndex(
   int timeframe,
   int shift,
   int period)
{
   int totalBars = iBars(Symbol(), timeframe);

   if(totalBars <= shift + period + 2)
      return(false);

   for(int barIndex = shift; barIndex < shift + period + 1; barIndex++)
   {
      if(iVolume(Symbol(), timeframe, barIndex) <= 0)
         return(false);
   }

   return(true);
}

bool CalculateRotorValue(
   int timeframe,
   int shift,
   double &rotorValue,
   int &validComponentCount)
{
   rotorValue = 0.0;
   validComponentCount = 0;

   int totalBars = iBars(Symbol(), timeframe);

   int requiredBars =
      (int)MathMax(
         SMAPeriod,
         MathMax(
            MomentumBars + 1,
            MathMax(
               MFIPeriod + 2,
               SimpleATRPeriod + 2
            )
         )
      );

   if(totalBars <= shift + requiredBars)
      return(false);

   double currentClosePrice = iClose(Symbol(), timeframe, shift);

   if(currentClosePrice <= 0.0)
      return(false);

   double simpleAverageTrueRangeValue = 0.0;

   if(!CalculateSimpleAverageTrueRange(
         timeframe,
         shift,
         SimpleATRPeriod,
         simpleAverageTrueRangeValue))
      return(false);

   if(simpleAverageTrueRangeValue <= ROTOR_EPS)
      return(false);

   double componentSum = 0.0;

   double simpleMovingAverageValue = 0.0;

   if(CalculateSimpleMovingAverage(
         timeframe,
         shift,
         SMAPeriod,
         simpleMovingAverageValue))
   {
      double structureComponent =
         ClipToUnitRange(
            (currentClosePrice - simpleMovingAverageValue) /
            simpleAverageTrueRangeValue
         );

      componentSum += structureComponent;
      validComponentCount++;
   }

   double momentumReferenceClosePrice =
      iClose(Symbol(), timeframe, shift + MomentumBars);

   if(momentumReferenceClosePrice > 0.0)
   {
      double momentumComponent =
         ClipToUnitRange(
            (currentClosePrice - momentumReferenceClosePrice) /
            simpleAverageTrueRangeValue
         );

      componentSum += momentumComponent;
      validComponentCount++;
   }

   if(HasUsableVolumeDataForMoneyFlowIndex(
         timeframe,
         shift,
         MFIPeriod))
   {
      double moneyFlowIndexValue =
         iMFI(Symbol(), timeframe, MFIPeriod, shift);

      if(moneyFlowIndexValue >= 0.0 && moneyFlowIndexValue <= 100.0)
      {
         double volumeComponent =
            ClipToUnitRange((moneyFlowIndexValue - 50.0) / 50.0);

         componentSum += volumeComponent;
         validComponentCount++;
      }
   }

   if(validComponentCount <= 0)
      return(false);

   rotorValue =
      ClipToUnitRange(componentSum / validComponentCount);

   return(true);
}

void LoadInitialRotorHistory()
{
   int validComponentCount = 0;

   g_currentRotorValueValid =
      CalculateRotorValue(
         Period(),
         1,
         g_currentClosedRotorValue,
         validComponentCount
      );

   g_previousRotorValueValid =
      CalculateRotorValue(
         Period(),
         2,
         g_previousClosedRotorValue,
         validComponentCount
      );

   g_olderRotorValueValid =
      CalculateRotorValue(
         Period(),
         3,
         g_olderClosedRotorValue,
         validComponentCount
      );
}

void UpdateRotorHistory()
{
   g_olderClosedRotorValue =
      g_previousClosedRotorValue;

   g_olderRotorValueValid =
      g_previousRotorValueValid;

   g_previousClosedRotorValue =
      g_currentClosedRotorValue;

   g_previousRotorValueValid =
      g_currentRotorValueValid;

   int validComponentCount = 0;

   g_currentRotorValueValid =
      CalculateRotorValue(
         Period(),
         1,
         g_currentClosedRotorValue,
         validComponentCount
      );

   if(!g_previousRotorValueValid)
   {
      g_previousRotorValueValid =
         CalculateRotorValue(
            Period(),
            2,
            g_previousClosedRotorValue,
            validComponentCount
         );
   }

   if(!g_olderRotorValueValid)
   {
      g_olderRotorValueValid =
         CalculateRotorValue(
            Period(),
            3,
            g_olderClosedRotorValue,
            validComponentCount
         );
   }
}

// ==================================================================
// MARKET MAP
// ==================================================================

ContextZone ClassifyContextZone(double contextPositionFraction)
{
   if(contextPositionFraction <= ExtremeBuyZoneMaximumFraction)
      return(ContextZoneExtremeBuy);

   if(contextPositionFraction <= PrimeBuyZoneMaximumFraction)
      return(ContextZonePrimeBuy);

   if(contextPositionFraction <= SecondaryBuyZoneMaximumFraction)
      return(ContextZoneSecondaryBuy);

   if(contextPositionFraction < SecondarySellZoneMinimumFraction)
      return(ContextZoneNeutral);

   if(contextPositionFraction < PrimeSellZoneMinimumFraction)
      return(ContextZoneSecondarySell);

   if(contextPositionFraction < ExtremeSellZoneMinimumFraction)
      return(ContextZonePrimeSell);

   return(ContextZoneExtremeSell);
}

bool BuildMarketMapResult(MarketMapResult &marketMapResult)
{
   marketMapResult.isReady = false;

   marketMapResult.contextOpenPrice =
      iOpen(Symbol(), (int)ContextTimeframe, 0);

   marketMapResult.contextHighPrice =
      iHigh(Symbol(), (int)ContextTimeframe, 0);

   marketMapResult.contextLowPrice =
      iLow(Symbol(), (int)ContextTimeframe, 0);

   if(marketMapResult.contextOpenPrice <= 0.0 ||
      marketMapResult.contextHighPrice <= marketMapResult.contextLowPrice ||
      marketMapResult.contextLowPrice <= 0.0)
      return(false);

   marketMapResult.contextRangePrice =
      marketMapResult.contextHighPrice -
      marketMapResult.contextLowPrice;

   RefreshRates();

   double currentPrice = (Bid + Ask) / 2.0;

   marketMapResult.contextPositionFraction =
      (currentPrice - marketMapResult.contextLowPrice) /
      marketMapResult.contextRangePrice;

   if(marketMapResult.contextPositionFraction < 0.0)
      marketMapResult.contextPositionFraction = 0.0;

   if(marketMapResult.contextPositionFraction > 1.0)
      marketMapResult.contextPositionFraction = 1.0;

   marketMapResult.contextAtrValue =
      iATR(
         Symbol(),
         (int)ContextTimeframe,
         ContextATRPeriod,
         1
      );

   if(marketMapResult.contextAtrValue <= 0.0)
      return(false);

   marketMapResult.contextMoveFromOpenInAtr =
      (currentPrice - marketMapResult.contextOpenPrice) /
      marketMapResult.contextAtrValue;

   marketMapResult.currentContextZone =
      ClassifyContextZone(
         marketMapResult.contextPositionFraction
      );

   marketMapResult.isReady = true;
   return(true);
}

void UpdateMarketMap()
{
   BuildMarketMapResult(g_latestMarketMap);
}

bool IsPrimeOrExtremeContextZone(int direction, ContextZone contextZone)
{
   if(direction == OP_BUY)
      return(
         contextZone == ContextZoneExtremeBuy ||
         contextZone == ContextZonePrimeBuy
      );

   if(direction == OP_SELL)
      return(
         contextZone == ContextZoneExtremeSell ||
         contextZone == ContextZonePrimeSell
      );

   return(false);
}

bool IsSecondaryContextZone(int direction, ContextZone contextZone)
{
   if(direction == OP_BUY)
      return(contextZone == ContextZoneSecondaryBuy);

   if(direction == OP_SELL)
      return(contextZone == ContextZoneSecondarySell);

   return(false);
}

// ==================================================================
// PIVOTS
// ==================================================================

bool IsConfirmedPivotLow(int timeframe, int shift)
{
   if(shift <= PivotRight)
      return(false);

   int totalBars = iBars(Symbol(), timeframe);

   if(totalBars <= shift + PivotLeft)
      return(false);

   double pivotLowPrice = iLow(Symbol(), timeframe, shift);

   if(pivotLowPrice <= 0.0)
      return(false);

   for(int olderBarOffset = 1; olderBarOffset <= PivotLeft; olderBarOffset++)
   {
      if(iLow(Symbol(), timeframe, shift + olderBarOffset) <= pivotLowPrice)
         return(false);
   }

   for(int newerBarOffset = 1; newerBarOffset <= PivotRight; newerBarOffset++)
   {
      if(iLow(Symbol(), timeframe, shift - newerBarOffset) < pivotLowPrice)
         return(false);
   }

   return(true);
}

bool IsConfirmedPivotHigh(int timeframe, int shift)
{
   if(shift <= PivotRight)
      return(false);

   int totalBars = iBars(Symbol(), timeframe);

   if(totalBars <= shift + PivotLeft)
      return(false);

   double pivotHighPrice = iHigh(Symbol(), timeframe, shift);

   if(pivotHighPrice <= 0.0)
      return(false);

   for(int olderBarOffset = 1; olderBarOffset <= PivotLeft; olderBarOffset++)
   {
      if(iHigh(Symbol(), timeframe, shift + olderBarOffset) >= pivotHighPrice)
         return(false);
   }

   for(int newerBarOffset = 1; newerBarOffset <= PivotRight; newerBarOffset++)
   {
      if(iHigh(Symbol(), timeframe, shift - newerBarOffset) > pivotHighPrice)
         return(false);
   }

   return(true);
}

bool FindMostRecentTwoPivotLows(
   int timeframe,
   int &recentPivotShift,
   int &previousPivotShift)
{
   recentPivotShift = -1;
   previousPivotShift = -1;

   int firstEligibleShift = PivotRight + 1;

   int maximumSearchShift =
      (int)MathMin(
         DivergenceSearchBars,
         iBars(Symbol(), timeframe) - PivotLeft - 1
      );

   for(int shift = firstEligibleShift; shift <= maximumSearchShift; shift++)
   {
      if(!IsConfirmedPivotLow(timeframe, shift))
         continue;

      if(recentPivotShift < 0)
         recentPivotShift = shift;
      else
      {
         previousPivotShift = shift;
         return(true);
      }
   }

   return(false);
}

bool FindMostRecentTwoPivotHighs(
   int timeframe,
   int &recentPivotShift,
   int &previousPivotShift)
{
   recentPivotShift = -1;
   previousPivotShift = -1;

   int firstEligibleShift = PivotRight + 1;

   int maximumSearchShift =
      (int)MathMin(
         DivergenceSearchBars,
         iBars(Symbol(), timeframe) - PivotLeft - 1
      );

   for(int shift = firstEligibleShift; shift <= maximumSearchShift; shift++)
   {
      if(!IsConfirmedPivotHigh(timeframe, shift))
         continue;

      if(recentPivotShift < 0)
         recentPivotShift = shift;
      else
      {
         previousPivotShift = shift;
         return(true);
      }
   }

   return(false);
}

// ==================================================================
// DIVERGENCE ENGINE
// ==================================================================

bool DivergenceModePasses(bool hasRsiDivergence, bool hasRotorDivergence)
{
   if(RequiredDivergenceMode == DivergenceAny)
      return(hasRsiDivergence || hasRotorDivergence);

   if(RequiredDivergenceMode == DivergenceBoth)
      return(hasRsiDivergence && hasRotorDivergence);

   if(RequiredDivergenceMode == DivergenceRSIOnly)
      return(hasRsiDivergence);

   if(RequiredDivergenceMode == DivergenceRotorOnly)
      return(hasRotorDivergence);

   return(false);
}

double CalculateDivergenceStrengthScore(DivergenceResult &divergenceResult)
{
   double priceExtensionScore =
      MathMin(30.0, divergenceResult.priceExtensionInAtr * 50.0);

   double rsiScore = 0.0;

   if(divergenceResult.hasRsiDivergence)
      rsiScore =
         MathMin(30.0, divergenceResult.rsiDivergenceDelta * 2.5);

   double rotorScore = 0.0;

   if(divergenceResult.hasRotorDivergence)
      rotorScore =
         MathMin(30.0, divergenceResult.rotorDivergenceDelta * 100.0);

   double dualConfirmationScore =
      (
         divergenceResult.hasRsiDivergence &&
         divergenceResult.hasRotorDivergence
         ?
         10.0
         :
         0.0
      );

   double totalScore =
      priceExtensionScore +
      rsiScore +
      rotorScore +
      dualConfirmationScore;

   if(totalScore > 100.0)
      totalScore = 100.0;

   return(totalScore);
}

DivergenceStrengthClass ClassifyDivergenceStrength(double divergenceStrengthScore)
{
   if(divergenceStrengthScore >= ExtremeDivergenceScoreMinimum)
      return(DivergenceStrengthExtreme);

   if(divergenceStrengthScore >= StrongDivergenceScoreMinimum)
      return(DivergenceStrengthStrong);

   if(divergenceStrengthScore >= NormalDivergenceScoreMinimum)
      return(DivergenceStrengthNormal);

   return(DivergenceStrengthWeak);
}

bool BuildDivergenceResult(int direction, DivergenceResult &divergenceResult)
{
   divergenceResult.isDetected = false;
   divergenceResult.hasRsiDivergence = false;
   divergenceResult.hasRotorDivergence = false;
   divergenceResult.recentPivotShift = -1;
   divergenceResult.previousPivotShift = -1;
   divergenceResult.recentPivotPrice = 0.0;
   divergenceResult.previousPivotPrice = 0.0;
   divergenceResult.priceExtensionInAtr = 0.0;
   divergenceResult.rsiDivergenceDelta = 0.0;
   divergenceResult.rotorDivergenceDelta = 0.0;
   divergenceResult.combinedStrengthScore = 0.0;
   divergenceResult.strengthClass = DivergenceStrengthWeak;

   int recentPivotShift = -1;
   int previousPivotShift = -1;

   if(direction == OP_BUY)
   {
      if(!FindMostRecentTwoPivotLows(
            Period(),
            recentPivotShift,
            previousPivotShift))
         return(false);

      divergenceResult.recentPivotPrice =
         iLow(Symbol(), Period(), recentPivotShift);

      divergenceResult.previousPivotPrice =
         iLow(Symbol(), Period(), previousPivotShift);
   }
   else
   if(direction == OP_SELL)
   {
      if(!FindMostRecentTwoPivotHighs(
            Period(),
            recentPivotShift,
            previousPivotShift))
         return(false);

      divergenceResult.recentPivotPrice =
         iHigh(Symbol(), Period(), recentPivotShift);

      divergenceResult.previousPivotPrice =
         iHigh(Symbol(), Period(), previousPivotShift);
   }
   else
      return(false);

   divergenceResult.recentPivotShift = recentPivotShift;
   divergenceResult.previousPivotShift = previousPivotShift;

   double pivotAtrValue = 0.0;

   if(!CalculateSimpleAverageTrueRange(
         Period(),
         recentPivotShift,
         SimpleATRPeriod,
         pivotAtrValue))
      return(false);

   if(direction == OP_BUY)
   {
      divergenceResult.priceExtensionInAtr =
         (divergenceResult.previousPivotPrice -
          divergenceResult.recentPivotPrice) /
         pivotAtrValue;
   }
   else
   {
      divergenceResult.priceExtensionInAtr =
         (divergenceResult.recentPivotPrice -
          divergenceResult.previousPivotPrice) /
         pivotAtrValue;
   }

   if(divergenceResult.priceExtensionInAtr < MinimumPricePivotDistanceATR)
      return(false);

   double recentRsiValue =
      iRSI(
         Symbol(),
         Period(),
         RSIPeriod,
         PRICE_CLOSE,
         recentPivotShift
      );

   double previousRsiValue =
      iRSI(
         Symbol(),
         Period(),
         RSIPeriod,
         PRICE_CLOSE,
         previousPivotShift
      );

   if(direction == OP_BUY)
   {
      divergenceResult.rsiDivergenceDelta =
         recentRsiValue - previousRsiValue;

      divergenceResult.hasRsiDivergence =
         (
            divergenceResult.recentPivotPrice <
            divergenceResult.previousPivotPrice
            &&
            divergenceResult.rsiDivergenceDelta >=
            MinimumRSIDivergenceDelta
         );
   }
   else
   {
      divergenceResult.rsiDivergenceDelta =
         previousRsiValue - recentRsiValue;

      divergenceResult.hasRsiDivergence =
         (
            divergenceResult.recentPivotPrice >
            divergenceResult.previousPivotPrice
            &&
            divergenceResult.rsiDivergenceDelta >=
            MinimumRSIDivergenceDelta
         );
   }

   double recentPivotRotorValue = 0.0;
   double previousPivotRotorValue = 0.0;
   int validComponentCount = 0;

   bool recentRotorValid =
      CalculateRotorValue(
         Period(),
         recentPivotShift,
         recentPivotRotorValue,
         validComponentCount
      );

   bool previousRotorValid =
      CalculateRotorValue(
         Period(),
         previousPivotShift,
         previousPivotRotorValue,
         validComponentCount
      );

   if(recentRotorValid && previousRotorValid)
   {
      if(direction == OP_BUY)
      {
         divergenceResult.rotorDivergenceDelta =
            recentPivotRotorValue -
            previousPivotRotorValue;

         divergenceResult.hasRotorDivergence =
            (
               divergenceResult.recentPivotPrice <
               divergenceResult.previousPivotPrice
               &&
               divergenceResult.rotorDivergenceDelta >=
               MinimumRotorDivergenceDelta
            );
      }
      else
      {
         divergenceResult.rotorDivergenceDelta =
            previousPivotRotorValue -
            recentPivotRotorValue;

         divergenceResult.hasRotorDivergence =
            (
               divergenceResult.recentPivotPrice >
               divergenceResult.previousPivotPrice
               &&
               divergenceResult.rotorDivergenceDelta >=
               MinimumRotorDivergenceDelta
            );
      }
   }

   if(!DivergenceModePasses(
         divergenceResult.hasRsiDivergence,
         divergenceResult.hasRotorDivergence))
      return(false);

   divergenceResult.combinedStrengthScore =
      CalculateDivergenceStrengthScore(divergenceResult);

   divergenceResult.strengthClass =
      ClassifyDivergenceStrength(
         divergenceResult.combinedStrengthScore
      );

   divergenceResult.isDetected = true;
   return(true);
}

// ==================================================================
// REGIME ENGINE
// ==================================================================

bool BuildHigherTimeframeRegimeResult(int direction, RegimeResult &regimeResult)
{
   regimeResult.isReady = false;
   regimeResult.currentRotorValue = 0.0;
   regimeResult.previousRotorValue = 0.0;
   regimeResult.rotorSlope = 0.0;
   regimeResult.regimeState = HigherTimeframeRegimeNeutral;

   int validComponentCount = 0;

   if(!CalculateRotorValue(
         (int)RegimeTimeframe,
         1,
         regimeResult.currentRotorValue,
         validComponentCount))
      return(false);

   if(!CalculateRotorValue(
         (int)RegimeTimeframe,
         2,
         regimeResult.previousRotorValue,
         validComponentCount))
      return(false);

   regimeResult.rotorSlope =
      regimeResult.currentRotorValue -
      regimeResult.previousRotorValue;

   if(direction == OP_BUY)
   {
      if(regimeResult.currentRotorValue > 0.0 &&
         regimeResult.rotorSlope >= 0.0)
         regimeResult.regimeState = HigherTimeframeRegimeAligned;
      else
      if(regimeResult.currentRotorValue <= 0.0 &&
         regimeResult.rotorSlope >= MinimumHigherTimeframeRecoverySlope)
         regimeResult.regimeState = HigherTimeframeRegimeRecovering;
      else
      if(MathAbs(regimeResult.currentRotorValue) <= HigherTimeframeNeutralBand &&
         MathAbs(regimeResult.rotorSlope) < MinimumHigherTimeframeRecoverySlope)
         regimeResult.regimeState = HigherTimeframeRegimeNeutral;
      else
         regimeResult.regimeState = HigherTimeframeRegimeOpposed;
   }
   else
   if(direction == OP_SELL)
   {
      if(regimeResult.currentRotorValue < 0.0 &&
         regimeResult.rotorSlope <= 0.0)
         regimeResult.regimeState = HigherTimeframeRegimeAligned;
      else
      if(regimeResult.currentRotorValue >= 0.0 &&
         regimeResult.rotorSlope <= -MinimumHigherTimeframeRecoverySlope)
         regimeResult.regimeState = HigherTimeframeRegimeRecovering;
      else
      if(MathAbs(regimeResult.currentRotorValue) <= HigherTimeframeNeutralBand &&
         MathAbs(regimeResult.rotorSlope) < MinimumHigherTimeframeRecoverySlope)
         regimeResult.regimeState = HigherTimeframeRegimeNeutral;
      else
         regimeResult.regimeState = HigherTimeframeRegimeOpposed;
   }
   else
      return(false);

   regimeResult.isReady = true;
   return(true);
}

// ==================================================================
// SETUP SNAPSHOT
// ==================================================================

void DetectAndCreateOrRefreshSetup(int direction)
{
   DivergenceResult divergenceResult;

   if(!BuildDivergenceResult(direction, divergenceResult))
      return;

   bool shouldCreateOrRefreshSetup = false;

   if(direction == OP_BUY)
   {
      if(g_buySetupState.currentState == DirectionalSignalIdle)
         shouldCreateOrRefreshSetup = true;
      else
      if(divergenceResult.recentPivotPrice <
         g_buySetupState.divergencePivotPrice - ROTOR_EPS)
         shouldCreateOrRefreshSetup = true;
   }
   else
   if(direction == OP_SELL)
   {
      if(g_sellSetupState.currentState == DirectionalSignalIdle)
         shouldCreateOrRefreshSetup = true;
      else
      if(divergenceResult.recentPivotPrice >
         g_sellSetupState.divergencePivotPrice + ROTOR_EPS)
         shouldCreateOrRefreshSetup = true;
   }

   if(!shouldCreateOrRefreshSetup)
      return;

   MarketMapResult marketMapSnapshot;

   if(!BuildMarketMapResult(marketMapSnapshot))
      return;

   RegimeResult regimeSnapshot;
   BuildHigherTimeframeRegimeResult(direction, regimeSnapshot);

   if(direction == OP_BUY)
   {
      g_buySetupState.currentState = DirectionalSignalArmed;
      g_buySetupState.setupCreatedTime = TimeCurrent();
      g_buySetupState.triggerConfirmedTime = 0;
      g_buySetupState.setupAgeInBars = 0;
      g_buySetupState.triggerAgeInBars = 0;
      g_buySetupState.divergencePivotPrice = divergenceResult.recentPivotPrice;
      g_buySetupState.setupContextPositionFraction = marketMapSnapshot.contextPositionFraction;
      g_buySetupState.setupContextZone = marketMapSnapshot.currentContextZone;
      g_buySetupState.setupRotorValue = g_currentClosedRotorValue;
      g_buySetupState.setupRegimeRotorValue = regimeSnapshot.currentRotorValue;
      g_buySetupState.setupRegimeRotorSlope = regimeSnapshot.rotorSlope;
      g_buySetupState.divergenceStrengthScore = divergenceResult.combinedStrengthScore;
      g_buySetupState.divergenceStrengthClass = divergenceResult.strengthClass;
      g_buySetupState.triggerType = RotorTriggerNone;
      g_buySetupState.triggerStrengthScore = 0.0;
      g_buySetupState.currentRegimeState = regimeSnapshot.regimeState;
      g_buySetupState.selectedQualityRoute = QualityRouteNone;
      g_buySetupState.primaryEntryAlreadyUsed = false;
      g_buySetupState.currentBlockReason = "";

      Print(
         "[ROTOR 3.30 SETUP]",
         " | Direction=BUY",
         " | Strength=", DivergenceStrengthText(g_buySetupState.divergenceStrengthClass),
         " | Score=", DoubleToString(g_buySetupState.divergenceStrengthScore,1),
         " | SetupZone=", ContextZoneText(g_buySetupState.setupContextZone),
         " | SetupPosition=", DoubleToString(g_buySetupState.setupContextPositionFraction * 100.0,1),
         "%"
      );
   }
   else
   {
      g_sellSetupState.currentState = DirectionalSignalArmed;
      g_sellSetupState.setupCreatedTime = TimeCurrent();
      g_sellSetupState.triggerConfirmedTime = 0;
      g_sellSetupState.setupAgeInBars = 0;
      g_sellSetupState.triggerAgeInBars = 0;
      g_sellSetupState.divergencePivotPrice = divergenceResult.recentPivotPrice;
      g_sellSetupState.setupContextPositionFraction = marketMapSnapshot.contextPositionFraction;
      g_sellSetupState.setupContextZone = marketMapSnapshot.currentContextZone;
      g_sellSetupState.setupRotorValue = g_currentClosedRotorValue;
      g_sellSetupState.setupRegimeRotorValue = regimeSnapshot.currentRotorValue;
      g_sellSetupState.setupRegimeRotorSlope = regimeSnapshot.rotorSlope;
      g_sellSetupState.divergenceStrengthScore = divergenceResult.combinedStrengthScore;
      g_sellSetupState.divergenceStrengthClass = divergenceResult.strengthClass;
      g_sellSetupState.triggerType = RotorTriggerNone;
      g_sellSetupState.triggerStrengthScore = 0.0;
      g_sellSetupState.currentRegimeState = regimeSnapshot.regimeState;
      g_sellSetupState.selectedQualityRoute = QualityRouteNone;
      g_sellSetupState.primaryEntryAlreadyUsed = false;
      g_sellSetupState.currentBlockReason = "";

      Print(
         "[ROTOR 3.30 SETUP]",
         " | Direction=SELL",
         " | Strength=", DivergenceStrengthText(g_sellSetupState.divergenceStrengthClass),
         " | Score=", DoubleToString(g_sellSetupState.divergenceStrengthScore,1),
         " | SetupZone=", ContextZoneText(g_sellSetupState.setupContextZone),
         " | SetupPosition=", DoubleToString(g_sellSetupState.setupContextPositionFraction * 100.0,1),
         "%"
      );
   }
}

// ==================================================================
// TRIGGER ENGINE
// ==================================================================

double CalculateTriggerStrengthScore(RotorTriggerResult &triggerResult)
{
   double baseScore = 0.0;

   if(triggerResult.triggerType == RotorTriggerFreshCross)
      baseScore = 45.0;
   else
   if(triggerResult.triggerType == RotorTriggerContinuation)
      baseScore = 35.0;
   else
   if(triggerResult.triggerType == RotorTriggerReAcceleration)
      baseScore = 40.0;

   double velocityScore =
      MathMin(30.0, MathAbs(triggerResult.rotorVelocity) * 150.0);

   double accelerationScore =
      MathMin(25.0, MathAbs(triggerResult.rotorAcceleration) * 125.0);

   double totalScore =
      baseScore +
      velocityScore +
      accelerationScore;

   if(totalScore > 100.0)
      totalScore = 100.0;

   return(totalScore);
}

bool BuildRotorTriggerResult(int direction, RotorTriggerResult &triggerResult)
{
   triggerResult.isDetected = false;
   triggerResult.triggerType = RotorTriggerNone;
   triggerResult.currentRotorValue = g_currentClosedRotorValue;
   triggerResult.previousRotorValue = g_previousClosedRotorValue;
   triggerResult.olderRotorValue = g_olderClosedRotorValue;
   triggerResult.rotorVelocity = 0.0;
   triggerResult.previousRotorVelocity = 0.0;
   triggerResult.rotorAcceleration = 0.0;
   triggerResult.triggerStrengthScore = 0.0;

   if(!g_currentRotorValueValid ||
      !g_previousRotorValueValid ||
      !g_olderRotorValueValid)
      return(false);

   triggerResult.rotorVelocity =
      triggerResult.currentRotorValue -
      triggerResult.previousRotorValue;

   triggerResult.previousRotorVelocity =
      triggerResult.previousRotorValue -
      triggerResult.olderRotorValue;

   triggerResult.rotorAcceleration =
      triggerResult.rotorVelocity -
      triggerResult.previousRotorVelocity;

   // Fresh cross.
   if(direction == OP_BUY)
   {
      if(triggerResult.previousRotorValue <= EntryLevel &&
         triggerResult.currentRotorValue > EntryLevel)
      {
         triggerResult.triggerType = RotorTriggerFreshCross;
         triggerResult.isDetected = true;
      }
   }
   else
   if(direction == OP_SELL)
   {
      if(triggerResult.previousRotorValue >= -EntryLevel &&
         triggerResult.currentRotorValue < -EntryLevel)
      {
         triggerResult.triggerType = RotorTriggerFreshCross;
         triggerResult.isDetected = true;
      }
   }

   // Continuation.
   if(!triggerResult.isDetected)
   {
      if(direction == OP_BUY)
      {
         if(triggerResult.currentRotorValue > EntryLevel &&
            triggerResult.rotorVelocity >= MinimumRotorContinuationVelocity)
         {
            triggerResult.triggerType = RotorTriggerContinuation;
            triggerResult.isDetected = true;
         }
      }
      else
      if(direction == OP_SELL)
      {
         if(triggerResult.currentRotorValue < -EntryLevel &&
            triggerResult.rotorVelocity <= -MinimumRotorContinuationVelocity)
         {
            triggerResult.triggerType = RotorTriggerContinuation;
            triggerResult.isDetected = true;
         }
      }
   }

   // Re-acceleration.
   if(!triggerResult.isDetected)
   {
      if(direction == OP_BUY)
      {
         bool hadPriorSoftening =
            (triggerResult.previousRotorVelocity <= 0.0);

         if(triggerResult.currentRotorValue > 0.0 &&
            triggerResult.rotorVelocity >= MinimumRotorReAccelerationVelocity &&
            triggerResult.rotorAcceleration >= MinimumRotorReAcceleration &&
            hadPriorSoftening)
         {
            triggerResult.triggerType = RotorTriggerReAcceleration;
            triggerResult.isDetected = true;
         }
      }
      else
      if(direction == OP_SELL)
      {
         bool hadPriorSoftening =
            (triggerResult.previousRotorVelocity >= 0.0);

         if(triggerResult.currentRotorValue < 0.0 &&
            triggerResult.rotorVelocity <= -MinimumRotorReAccelerationVelocity &&
            triggerResult.rotorAcceleration <= -MinimumRotorReAcceleration &&
            hadPriorSoftening)
         {
            triggerResult.triggerType = RotorTriggerReAcceleration;
            triggerResult.isDetected = true;
         }
      }
   }

   if(!triggerResult.isDetected)
      return(false);

   triggerResult.triggerStrengthScore =
      CalculateTriggerStrengthScore(triggerResult);

   return(true);
}

void DetectAndApplyTrigger(int direction)
{
   if(direction == OP_BUY)
   {
      if(g_buySetupState.currentState != DirectionalSignalArmed)
         return;
   }
   else
   if(direction == OP_SELL)
   {
      if(g_sellSetupState.currentState != DirectionalSignalArmed)
         return;
   }
   else
      return;

   RotorTriggerResult triggerResult;

   if(!BuildRotorTriggerResult(direction, triggerResult))
      return;

   if(direction == OP_BUY)
   {
      g_buySetupState.currentState = DirectionalSignalTriggered;
      g_buySetupState.triggerConfirmedTime = TimeCurrent();
      g_buySetupState.triggerAgeInBars = 0;
      g_buySetupState.triggerType = triggerResult.triggerType;
      g_buySetupState.triggerStrengthScore = triggerResult.triggerStrengthScore;
      g_buySetupState.currentBlockReason = "";

      Print(
         "[ROTOR 3.30 TRIGGER]",
         " | Direction=BUY",
         " | Type=", TriggerTypeText(triggerResult.triggerType),
         " | Strength=", DoubleToString(triggerResult.triggerStrengthScore,1)
      );
   }
   else
   {
      g_sellSetupState.currentState = DirectionalSignalTriggered;
      g_sellSetupState.triggerConfirmedTime = TimeCurrent();
      g_sellSetupState.triggerAgeInBars = 0;
      g_sellSetupState.triggerType = triggerResult.triggerType;
      g_sellSetupState.triggerStrengthScore = triggerResult.triggerStrengthScore;
      g_sellSetupState.currentBlockReason = "";

      Print(
         "[ROTOR 3.30 TRIGGER]",
         " | Direction=SELL",
         " | Type=", TriggerTypeText(triggerResult.triggerType),
         " | Strength=", DoubleToString(triggerResult.triggerStrengthScore,1)
      );
   }
}

// ==================================================================
// QUALITY ROUTER
// ==================================================================

QualityRoute SelectQualityRoute(
   int direction,
   DirectionSetupState &directionState,
   ContextZone currentContextZone,
   HigherTimeframeRegime currentRegimeState)
{
   bool isNormalOrBetter =
      (
         directionState.divergenceStrengthClass == DivergenceStrengthNormal ||
         directionState.divergenceStrengthClass == DivergenceStrengthStrong ||
         directionState.divergenceStrengthClass == DivergenceStrengthExtreme
      );

   bool isStrongOrBetter =
      (
         directionState.divergenceStrengthClass == DivergenceStrengthStrong ||
         directionState.divergenceStrengthClass == DivergenceStrengthExtreme
      );

   bool isExtreme =
      (directionState.divergenceStrengthClass == DivergenceStrengthExtreme);

   bool isAligned =
      (currentRegimeState == HigherTimeframeRegimeAligned);

   bool isAlignedOrRecovering =
      (
         currentRegimeState == HigherTimeframeRegimeAligned ||
         currentRegimeState == HigherTimeframeRegimeRecovering
      );

   bool isPrimeOrExtreme =
      IsPrimeOrExtremeContextZone(direction, currentContextZone);

   bool isSecondary =
      IsSecondaryContextZone(direction, currentContextZone);

   // PATH A
   if(isPrimeOrExtreme &&
      isNormalOrBetter &&
      directionState.triggerType == RotorTriggerFreshCross &&
      isAlignedOrRecovering)
      return(QualityRoutePrimeFreshCross);

   // PATH B
   if(isPrimeOrExtreme &&
      isStrongOrBetter &&
      directionState.triggerType == RotorTriggerContinuation &&
      isAlignedOrRecovering)
      return(QualityRoutePrimeContinuation);

   // PATH C
   if(isSecondary &&
      isStrongOrBetter &&
      (
         directionState.triggerType == RotorTriggerFreshCross ||
         directionState.triggerType == RotorTriggerReAcceleration
      )
      &&
      isAligned)
      return(QualityRouteSecondaryStrongReaction);

   // PATH D
   if(isPrimeOrExtreme &&
      isExtreme &&
      directionState.triggerType == RotorTriggerReAcceleration &&
      (
         currentRegimeState == HigherTimeframeRegimeRecovering ||
         currentRegimeState == HigherTimeframeRegimeNeutral
      ))
      return(QualityRouteExtremeRecovery);

   return(QualityRouteNone);
}

double CalculateOverallQualityScore(
   int direction,
   DirectionSetupState &directionState,
   ContextZone currentContextZone,
   HigherTimeframeRegime currentRegimeState)
{
   double contextScore = 0.0;

   if(IsPrimeOrExtremeContextZone(direction, currentContextZone))
   {
      if(currentContextZone == ContextZoneExtremeBuy ||
         currentContextZone == ContextZoneExtremeSell)
         contextScore = 25.0;
      else
         contextScore = 20.0;
   }
   else
   if(IsSecondaryContextZone(direction, currentContextZone))
      contextScore = 12.0;

   double divergenceScore =
      MathMin(30.0, directionState.divergenceStrengthScore * 0.30);

   double triggerScore =
      MathMin(25.0, directionState.triggerStrengthScore * 0.25);

   double regimeScore = 0.0;

   if(currentRegimeState == HigherTimeframeRegimeAligned)
      regimeScore = 20.0;
   else
   if(currentRegimeState == HigherTimeframeRegimeRecovering)
      regimeScore = 14.0;
   else
   if(currentRegimeState == HigherTimeframeRegimeNeutral)
      regimeScore = 6.0;

   double freshnessScore = 0.0;

   if(directionState.triggerAgeInBars == 0)
      freshnessScore = 10.0;
   else
   if(directionState.triggerAgeInBars == 1)
      freshnessScore = 7.0;
   else
   if(directionState.triggerAgeInBars == 2)
      freshnessScore = 4.0;
   else
      freshnessScore = 2.0;

   double totalQualityScore =
      contextScore +
      divergenceScore +
      triggerScore +
      regimeScore +
      freshnessScore;

   if(totalQualityScore > 100.0)
      totalQualityScore = 100.0;

   return(totalQualityScore);
}

// ==================================================================
// GEOMETRY
// ==================================================================

bool BuildTradeGeometryResult(
   int direction,
   double divergencePivotPrice,
   TradeGeometryResult &geometryResult)
{
   geometryResult.isReady = false;
   geometryResult.entryPrice = 0.0;
   geometryResult.stopLossPrice = 0.0;
   geometryResult.takeProfitPrice = 0.0;
   geometryResult.stopLossDistancePoints = 0.0;
   geometryResult.takeProfitDistancePoints = 0.0;
   geometryResult.rewardRiskRatio = 0.0;
   geometryResult.roomToTargetInAtr = 0.0;
   geometryResult.rejectionReason = "";

   if(divergencePivotPrice <= 0.0)
   {
      geometryResult.rejectionReason = "INVALID PIVOT PRICE";
      return(false);
   }

   if(!g_latestMarketMap.isReady)
   {
      geometryResult.rejectionReason = "MARKET MAP NOT READY";
      return(false);
   }

   double workingAtrValue = 0.0;

   if(!CalculateSimpleAverageTrueRange(
         Period(),
         1,
         SimpleATRPeriod,
         workingAtrValue))
   {
      geometryResult.rejectionReason = "WORKING ATR NOT READY";
      return(false);
   }

   RefreshRates();

   double riskDistancePrice = 0.0;
   double rewardDistancePrice = 0.0;

   if(direction == OP_BUY)
   {
      geometryResult.entryPrice = Ask;

      geometryResult.stopLossPrice =
         NormalizeDouble(
            divergencePivotPrice -
            workingAtrValue * StopATRBufferMultiplier,
            Digits
         );

      geometryResult.takeProfitPrice =
         NormalizeDouble(
            g_latestMarketMap.contextLowPrice +
            g_latestMarketMap.contextRangePrice *
            BuySpatialTargetFraction,
            Digits
         );

      riskDistancePrice =
         geometryResult.entryPrice -
         geometryResult.stopLossPrice;

      rewardDistancePrice =
         geometryResult.takeProfitPrice -
         geometryResult.entryPrice;
   }
   else
   if(direction == OP_SELL)
   {
      geometryResult.entryPrice = Bid;

      geometryResult.stopLossPrice =
         NormalizeDouble(
            divergencePivotPrice +
            workingAtrValue * StopATRBufferMultiplier,
            Digits
         );

      geometryResult.takeProfitPrice =
         NormalizeDouble(
            g_latestMarketMap.contextLowPrice +
            g_latestMarketMap.contextRangePrice *
            SellSpatialTargetFraction,
            Digits
         );

      riskDistancePrice =
         geometryResult.stopLossPrice -
         geometryResult.entryPrice;

      rewardDistancePrice =
         geometryResult.entryPrice -
         geometryResult.takeProfitPrice;
   }
   else
   {
      geometryResult.rejectionReason = "INVALID DIRECTION";
      return(false);
   }

   if(riskDistancePrice <= 0.0)
   {
      geometryResult.rejectionReason = "INVALID SL GEOMETRY";
      return(false);
   }

   if(rewardDistancePrice <= 0.0)
   {
      geometryResult.rejectionReason = "TARGET BEHIND PRICE";
      return(false);
   }

   geometryResult.stopLossDistancePoints =
      riskDistancePrice / Point;

   geometryResult.takeProfitDistancePoints =
      rewardDistancePrice / Point;

   geometryResult.rewardRiskRatio =
      rewardDistancePrice / riskDistancePrice;

   geometryResult.roomToTargetInAtr =
      rewardDistancePrice / workingAtrValue;

   double brokerStopLevelPoints =
      MarketInfo(Symbol(), MODE_STOPLEVEL);

   if(brokerStopLevelPoints > 0.0)
   {
      if(geometryResult.stopLossDistancePoints < brokerStopLevelPoints)
      {
         geometryResult.rejectionReason = "SL INSIDE BROKER STOPLEVEL";
         return(false);
      }

      if(geometryResult.takeProfitDistancePoints < brokerStopLevelPoints)
      {
         geometryResult.rejectionReason = "TP INSIDE BROKER STOPLEVEL";
         return(false);
      }
   }

   geometryResult.isReady = true;
   return(true);
}

// ==================================================================
// FILTERS / EXECUTION
// ==================================================================

bool DirectionIsAllowed(int direction)
{
   if(direction == OP_BUY)
      return(
         AllowedTradeDirection == TradeBuyOnly ||
         AllowedTradeDirection == TradeBoth
      );

   if(direction == OP_SELL)
      return(
         AllowedTradeDirection == TradeSellOnly ||
         AllowedTradeDirection == TradeBoth
      );

   return(false);
}

bool ExecutionFiltersPass(int direction, string &rejectionReason)
{
   rejectionReason = "";

   if(!DirectionIsAllowed(direction))
   {
      rejectionReason = "DIRECTION DISALLOWED";
      return(false);
   }

   if(CountOwnOpenPositions() > 0)
   {
      rejectionReason = "POSITION ALREADY OPEN";
      return(false);
   }

   RefreshRates();

   double currentSpreadPoints = (Ask - Bid) / Point;

   if(currentSpreadPoints > MaximumSpreadPoints)
   {
      rejectionReason = "SPREAD TOO HIGH";
      return(false);
   }

   if(BlockSundayTrading && DayOfWeek() == 0)
   {
      rejectionReason = "SUNDAY BLOCK";
      return(false);
   }

   if(UseFridayCutoff &&
      DayOfWeek() == 5 &&
      Hour() >= FridayCutoffHour)
   {
      rejectionReason = "FRIDAY CUTOFF";
      return(false);
   }

   if(UseMinimumATRFilter)
   {
      double workingAtrValue = 0.0;

      if(!CalculateSimpleAverageTrueRange(
            Period(),
            1,
            SimpleATRPeriod,
            workingAtrValue))
      {
         rejectionReason = "WORKING ATR NOT READY";
         return(false);
      }

      if(workingAtrValue / Point < MinimumWorkingATRPoints)
      {
         rejectionReason = "ATR BELOW MINIMUM";
         return(false);
      }
   }

   return(true);
}

void SetDirectionBlockReason(int direction, string blockReason)
{
   if(direction == OP_BUY)
      g_buySetupState.currentBlockReason = blockReason;
   else
   if(direction == OP_SELL)
      g_sellSetupState.currentBlockReason = blockReason;
}

void EvaluateTriggeredSetupAndTrade(int direction)
{
   DirectionSetupState localDirectionState;

   if(direction == OP_BUY)
      localDirectionState = g_buySetupState;
   else
      localDirectionState = g_sellSetupState;

   if(localDirectionState.currentState != DirectionalSignalTriggered)
      return;

   if(localDirectionState.primaryEntryAlreadyUsed)
      return;

   if(!g_latestMarketMap.isReady)
   {
      SetDirectionBlockReason(direction, "MARKET MAP NOT READY");
      return;
   }

   RegimeResult regimeResult;

   if(!BuildHigherTimeframeRegimeResult(direction, regimeResult))
   {
      SetDirectionBlockReason(direction, "REGIME NOT READY");
      return;
   }

   if(direction == OP_BUY)
      g_buySetupState.currentRegimeState = regimeResult.regimeState;
   else
      g_sellSetupState.currentRegimeState = regimeResult.regimeState;

   QualityRoute selectedQualityRoute =
      SelectQualityRoute(
         direction,
         localDirectionState,
         g_latestMarketMap.currentContextZone,
         regimeResult.regimeState
      );

   double overallQualityScore =
      CalculateOverallQualityScore(
         direction,
         localDirectionState,
         g_latestMarketMap.currentContextZone,
         regimeResult.regimeState
      );

   if(selectedQualityRoute == QualityRouteNone)
   {
      SetDirectionBlockReason(direction, "NO QUALITY ROUTE");
      return;
   }

   if(UseQualityScoreAsEntryVeto &&
      overallQualityScore < MinimumQualityScore)
   {
      SetDirectionBlockReason(direction, "QUALITY SCORE BELOW MINIMUM");
      return;
   }

   TradeGeometryResult geometryResult;

   if(!BuildTradeGeometryResult(
         direction,
         localDirectionState.divergencePivotPrice,
         geometryResult))
   {
      SetDirectionBlockReason(
         direction,
         geometryResult.rejectionReason
      );
      return;
   }

   if(UseGeometryAsEntryVeto)
   {
      if(geometryResult.rewardRiskRatio < MinimumRewardRiskRatio)
      {
         SetDirectionBlockReason(direction, "R:R BELOW MINIMUM");
         return;
      }

      if(geometryResult.roomToTargetInAtr < MinimumRoomToTargetInAtr)
      {
         SetDirectionBlockReason(direction, "ROOM TO TARGET TOO SMALL");
         return;
      }
   }

   string executionRejectionReason = "";

   if(!ExecutionFiltersPass(direction, executionRejectionReason))
   {
      SetDirectionBlockReason(direction, executionRejectionReason);
      return;
   }

   double normalizedLotSize = NormalizeLotSize(FixedLotSize);

   if(normalizedLotSize <= 0.0)
   {
      SetDirectionBlockReason(direction, "INVALID LOT");
      return;
   }

   if(AccountFreeMarginCheck(
         Symbol(),
         direction,
         normalizedLotSize) <= 0.0)
   {
      SetDirectionBlockReason(direction, "INSUFFICIENT FREE MARGIN");
      return;
   }

   int openedTicket =
      OpenTrade(
         direction,
         normalizedLotSize,
         geometryResult.stopLossPrice,
         geometryResult.takeProfitPrice
      );

   if(openedTicket <= 0)
      return;

   if(direction == OP_BUY)
   {
      g_buySetupState.primaryEntryAlreadyUsed = true;
      g_buySetupState.selectedQualityRoute = selectedQualityRoute;
      g_buySetupState.currentBlockReason = "";
   }
   else
   {
      g_sellSetupState.primaryEntryAlreadyUsed = true;
      g_sellSetupState.selectedQualityRoute = selectedQualityRoute;
      g_sellSetupState.currentBlockReason = "";
   }

   g_lastAction =
      "OPENED " +
      DirectionText(direction) +
      " " +
      QualityRouteText(selectedQualityRoute);

   Print(
      "[ROTOR 3.30 ENTRY]",
      " | Direction=", DirectionText(direction),
      " | Route=", QualityRouteText(selectedQualityRoute),
      " | SignalTF=", TimeframeText(Period()),
      " | ContextTF=", TimeframeText((int)ContextTimeframe),
      " | ContextZone=", ContextZoneText(g_latestMarketMap.currentContextZone),
      " | RegimeTF=", TimeframeText((int)RegimeTimeframe),
      " | Regime=", RegimeText(regimeResult.regimeState),
      " | Divergence=", DivergenceStrengthText(localDirectionState.divergenceStrengthClass),
      " | Trigger=", TriggerTypeText(localDirectionState.triggerType),
      " | Quality=", DoubleToString(overallQualityScore,1),
      " | RR=", DoubleToString(geometryResult.rewardRiskRatio,2),
      " | RoomATR=", DoubleToString(geometryResult.roomToTargetInAtr,2),
      " | Balance=", DoubleToString(AccountBalance(),2)
   );
}

int OpenTrade(
   int direction,
   double lotSize,
   double stopLossPrice,
   double takeProfitPrice)
{
   if(direction != OP_BUY && direction != OP_SELL)
      return(-1);

   if(CountOwnOpenPositions() > 0)
      return(-1);

   for(int attemptNumber = 1;
       attemptNumber <= OrderSendRetries;
       attemptNumber++)
   {
      RefreshRates();

      double openPrice =
         (direction == OP_BUY ? Ask : Bid);

      ResetLastError();

      int ticket =
         OrderSend(
            Symbol(),
            direction,
            lotSize,
            openPrice,
            SlippagePoints,
            stopLossPrice,
            takeProfitPrice,
            (direction == OP_BUY ? "ROTOR_330_BUY" : "ROTOR_330_SELL"),
            MagicNumber,
            0,
            clrNONE
         );

      if(ticket > 0)
         return(ticket);

      int errorCode = GetLastError();

      Print(
         "[ROTOR 3.30] OrderSend failed",
         " | Attempt=", attemptNumber,
         " | Error=", errorCode
      );

      Sleep(150);
   }

   return(-1);
}

void ManageTrade()
{
   // Broker SL / TP only in this research version.
}

int CountOwnOpenPositions()
{
   int ownOpenPositionCount = 0;

   for(int orderIndex = 0;
       orderIndex < OrdersTotal();
       orderIndex++)
   {
      if(!OrderSelect(orderIndex, SELECT_BY_POS, MODE_TRADES))
         continue;

      if(OrderSymbol() != Symbol())
         continue;

      if(OrderMagicNumber() != MagicNumber)
         continue;

      if(OrderType() == OP_BUY || OrderType() == OP_SELL)
         ownOpenPositionCount++;
   }

   return(ownOpenPositionCount);
}

double NormalizeLotSize(double requestedLotSize)
{
   double minimumLotSize = MarketInfo(Symbol(), MODE_MINLOT);
   double maximumLotSize = MarketInfo(Symbol(), MODE_MAXLOT);
   double lotStepSize    = MarketInfo(Symbol(), MODE_LOTSTEP);

   if(minimumLotSize <= 0.0)
      minimumLotSize = 0.01;

   if(maximumLotSize <= 0.0)
      maximumLotSize = requestedLotSize;

   if(lotStepSize <= 0.0)
      lotStepSize = minimumLotSize;

   double normalizedLotSize = requestedLotSize;

   if(normalizedLotSize < minimumLotSize)
      normalizedLotSize = minimumLotSize;

   if(normalizedLotSize > maximumLotSize)
      normalizedLotSize = maximumLotSize;

   normalizedLotSize =
      MathFloor(
         (normalizedLotSize + ROTOR_EPS) /
         lotStepSize
      )
      *
      lotStepSize;

   int lotDigits = 2;

   if(lotStepSize < 0.01)
      lotDigits = 3;

   if(lotStepSize < 0.001)
      lotDigits = 4;

   return(NormalizeDouble(normalizedLotSize, lotDigits));
}

// ==================================================================
// DASHBOARD
// ==================================================================

string SignalStateText(DirectionSetupState &directionState)
{
   if(directionState.currentState == DirectionalSignalIdle)
      return("IDLE");

   if(directionState.currentState == DirectionalSignalArmed)
      return(
         "ARMED age=" +
         IntegerToString(directionState.setupAgeInBars)
      );

   if(directionState.currentState == DirectionalSignalTriggered)
      return(
         "TRIGGERED age=" +
         IntegerToString(directionState.triggerAgeInBars)
      );

   return("UNKNOWN");
}

void UpdateStatusPanel()
{
   string panelText = "";

   panelText += "ROTOR CONTEXT ENGINE 3.30 MULTI-PATH\n";
   panelText += "---------------------------------\n";

   panelText +=
      "SIGNAL TF      : " +
      TimeframeText(Period()) +
      "\n";

   panelText +=
      "CONTEXT TF     : " +
      TimeframeText((int)ContextTimeframe) +
      "\n";

   panelText +=
      "REGIME TF      : " +
      TimeframeText((int)RegimeTimeframe) +
      "\n";

   if((int)ContextTimeframe < Period())
      panelText += "WARNING         : Context TF < Signal TF\n";

   if((int)RegimeTimeframe < Period())
      panelText += "WARNING         : Regime TF < Signal TF\n";

   panelText += "---------------------------------\n";

   if(g_latestMarketMap.isReady)
   {
      panelText +=
         "CONTEXT POS    : " +
         DoubleToString(
            g_latestMarketMap.contextPositionFraction * 100.0,
            1
         )
         +
         "%\n";

      panelText +=
         "CONTEXT ZONE   : " +
         ContextZoneText(
            g_latestMarketMap.currentContextZone
         )
         +
         "\n";

      panelText +=
         "CONTEXT MOVE   : " +
         DoubleToString(
            g_latestMarketMap.contextMoveFromOpenInAtr,
            2
         )
         +
         " ATR\n";
   }
   else
      panelText += "CONTEXT         : NOT READY\n";

   panelText += "---------------------------------\n";

   panelText +=
      "BUY STATE      : " +
      SignalStateText(g_buySetupState) +
      "\n";

   panelText +=
      "BUY DIV        : " +
      DivergenceStrengthText(
         g_buySetupState.divergenceStrengthClass
      )
      +
      " " +
      DoubleToString(
         g_buySetupState.divergenceStrengthScore,
         1
      )
      +
      "\n";

   panelText +=
      "BUY TRIGGER    : " +
      TriggerTypeText(
         g_buySetupState.triggerType
      )
      +
      "\n";

   panelText +=
      "BUY REGIME     : " +
      RegimeText(
         g_buySetupState.currentRegimeState
      )
      +
      "\n";

   panelText +=
      "BUY ROUTE      : " +
      QualityRouteText(
         g_buySetupState.selectedQualityRoute
      )
      +
      "\n";

   panelText +=
      "BUY BLOCK      : " +
      (
         StringLen(g_buySetupState.currentBlockReason) > 0
         ?
         g_buySetupState.currentBlockReason
         :
         "-"
      )
      +
      "\n";

   panelText += "---------------------------------\n";

   panelText +=
      "SELL STATE     : " +
      SignalStateText(g_sellSetupState) +
      "\n";

   panelText +=
      "SELL DIV       : " +
      DivergenceStrengthText(
         g_sellSetupState.divergenceStrengthClass
      )
      +
      " " +
      DoubleToString(
         g_sellSetupState.divergenceStrengthScore,
         1
      )
      +
      "\n";

   panelText +=
      "SELL TRIGGER   : " +
      TriggerTypeText(
         g_sellSetupState.triggerType
      )
      +
      "\n";

   panelText +=
      "SELL REGIME    : " +
      RegimeText(
         g_sellSetupState.currentRegimeState
      )
      +
      "\n";

   panelText +=
      "SELL ROUTE     : " +
      QualityRouteText(
         g_sellSetupState.selectedQualityRoute
      )
      +
      "\n";

   panelText +=
      "SELL BLOCK     : " +
      (
         StringLen(g_sellSetupState.currentBlockReason) > 0
         ?
         g_sellSetupState.currentBlockReason
         :
         "-"
      )
      +
      "\n";

   panelText += "---------------------------------\n";

   panelText +=
      "POSITIONS      : " +
      IntegerToString(CountOwnOpenPositions()) +
      "\n";

   panelText +=
      "LAST ACTION    : " +
      g_lastAction +
      "\n";

   Comment(panelText);
}
//+------------------------------------------------------------------+

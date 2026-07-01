# C-Script control blocks

PLECS `CScript` blocks run user C code — the realistic way to implement digital
controllers, modulators and state machines. The engine authors them like any
other component; PLECS compiles the code at simulation time.

## Component structure (from inverter_with_cscript_based_modulator)
Params: `NumInputs`, `NumOutputs`, `NumContStates`, `NumDiscStates`, `NumZCSignals`,
`DirectFeedthrough`, `Ts` (sample time; may reference a model variable),
`Parameters` (space-separated model expressions passed in), and the code sections
`Declarations`, `StartFcn`, `OutputFcn`, `UpdateFcn`, `DerivativeFcn`, `TerminateFcn`.

Terminals: inputs are `1..NumInputs`, outputs `NumInputs+1..NumInputs+NumOutputs`.
(The KB marks `CScript` as a variable-port block so validation allows any index.)

## Code macros (verified on PLECS 4.9.5)
- `Input(i)` — read input i (0-based).
- `Output(i) = x;` — write output i.
- `DiscState(i)` — persistent discrete state (update in `UpdateFcn`).
- `ParamRealData(i, 0)` — read parameter i from the `Parameters` list (0-based).

## Verified example: digital PI voltage controller (golden_models/agent_buck_cscript)
`Parameters = "Vref_v Kp Ki Tc"`, `NumInputs=1` (Vo), `NumOutputs=1` (duty),
`NumDiscStates=1` (integrator), `Ts=Tc`.

```c
// OutputFcn
double Vref=ParamRealData(0,0), Kp=ParamRealData(1,0);
double err=Vref-Input(0);
double duty=Kp*err+DiscState(0);
if(duty>0.95) duty=0.95; if(duty<0.02) duty=0.02;
Output(0)=duty;
// UpdateFcn
double Vref=ParamRealData(0,0), Ki=ParamRealData(2,0), Tc=ParamRealData(3,0);
double integ=DiscState(0)+Ki*Tc*(Vref-Input(0));
if(integ>0.95) integ=0.95; if(integ<0.0) integ=0.0;
DiscState(0)=integ;
```
Duty -> RelationalOperator vs TriangleGenerator -> MOSFET gate. On live PLECS:
Vo = 15.00 V (target 15), 0.25% overshoot, 7.9 ms settling; tracks Vref=10 -> 10.00 V.

# OEC Physics Foundation API v0

## P1 contract: `dc_power_flow`

`dc_power_flow` is the canonical P1 **linear DC power-flow model for meshed
networks**. Wave 1 freezes the contract; numerical implementation arrives in a
later wave.

Documented signature:

```python
def dc_power_flow(
    topology: NetworkTopology,
    impedances: tuple[BranchImpedance, ...],
    injections: tuple[NodalInjection, ...],
) -> DCPowerFlowResult: ...
```

### Inputs

- `topology`: explicit nodes, branches, branch endpoints, connectivity, and one
  declared reference node;
- `impedances`: branch impedances keyed to every in-service branch;
- `injections`: signed active-power injections keyed to nodes, using one stated
  sign convention and balancing at the reference node.

### Outputs

- voltage magnitudes in per-unit, fixed/reported according to the DC
  linearization;
- solved nodal voltage angles relative to the declared reference node;
- signed active-power flow for every branch, with branch orientation preserved.

### Hypotheses

- linear DC approximation on a connected meshed network;
- `R >> X`;
- voltage-angle differences are small;
- voltage magnitudes are approximately `1 pu`;
- reactive power and losses are outside this v0 contract;
- inputs use a consistent per-unit base and an explicit reference node.

### Oracles

Acceptance uses small hand-solved meshed cases supplied as golden fixtures.
Each golden fixes the topology, reference node, impedances, injections, voltage
angles, per-unit voltage magnitudes, oriented branch flows, and numerical
tolerance. The implementation must reproduce those values and nodal active-power
balance; self-generated outputs are not an oracle.

## Conservation ownership

`oec.physics.conservation` is the sole owner of generic residual evaluation and
the `abs(residual) <= atol + rtol * scale` decision. The existing
`oec.kernel.energy.metrics.energy_balance` API remains unchanged in 2.6.0 and is
treated as an energy-scoped consumer/parity target. It is not a second owner.

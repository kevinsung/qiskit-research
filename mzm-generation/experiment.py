import functools
import itertools
from collections import namedtuple
from typing import Iterable, List, Optional, Sequence, Tuple

from qiskit import QuantumCircuit
from qiskit.providers import Backend
from qiskit_experiments.framework import BaseExperiment
from qiskit_nature.circuit.library import FermionicGaussianState

from mzm_generation import (
    kitaev_hamiltonian,
    measure_pauli_string,
    measurement_pauli_strings,
)

CircuitParameters = namedtuple(
    "CircuitParameters",
    [
        "tunneling",
        "superconducting",
        "chemical_potential",
        "occupied_orbitals",
        "measurement_basis",
        "measurement_label",
    ],
)


class KitaevHamiltonianExperiment(BaseExperiment):
    """Prepare and measure eigenstates of the Kitaev Hamiltonian."""

    def __init__(
        self,
        experiment_id: str,
        qubits: Sequence[int],
        tunneling_values: float,
        superconducting_values: float,
        chemical_potential_values: float,
        occupied_orbitals_list: Sequence[Tuple[int]],
        backend: Optional[Backend] = None,
    ) -> None:
        self.experiment_id = experiment_id
        self.n_modes = len(qubits)
        self.tunneling_values = tunneling_values
        self.superconducting_values = superconducting_values
        self.chemical_potential_values = chemical_potential_values
        self.occupied_orbitals_list = occupied_orbitals_list
        super().__init__(qubits=qubits, backend=backend)

    def circuits(self) -> List[QuantumCircuit]:
        return list(self._circuits())

    def _circuits(self) -> Iterable[QuantumCircuit]:
        for circuit_params in self.circuit_parameters():
            yield self._generate_circuit(circuit_params)

    def _generate_circuit(self, circuit_params: CircuitParameters) -> QuantumCircuit:
        base_circuit = self._base_circuit(
            circuit_params.tunneling,
            circuit_params.superconducting,
            circuit_params.chemical_potential,
            circuit_params.occupied_orbitals,
        )
        if circuit_params.measurement_basis == "pauli":
            circuit = measure_pauli_string(
                base_circuit, circuit_params.measurement_label
            )
            circuit.metadata = {"params": circuit_params}
            return circuit

    @functools.lru_cache
    def _base_circuit(
        self,
        tunneling: float,
        superconducting: float,
        chemical_potential: float,
        occupied_orbitals: Tuple[int],
    ) -> QuantumCircuit:
        hamiltonian = kitaev_hamiltonian(
            self.n_modes,
            tunneling=tunneling,
            superconducting=superconducting,
            chemical_potential=chemical_potential,
        )
        transformation_matrix, _, _ = hamiltonian.diagonalizing_bogoliubov_transform()
        return FermionicGaussianState(transformation_matrix, occupied_orbitals)

    def circuit_parameters(self) -> Iterable[CircuitParameters]:
        for (
            tunneling,
            superconducting,
            chemical_potential,
            occupied_orbitals,
        ) in itertools.product(
            self.tunneling_values,
            self.superconducting_values,
            self.chemical_potential_values,
            self.occupied_orbitals_list,
        ):
            for pauli_string in measurement_pauli_strings(self.n_modes):
                yield CircuitParameters(
                    tunneling=tunneling,
                    superconducting=superconducting,
                    chemical_potential=chemical_potential,
                    occupied_orbitals=occupied_orbitals,
                    measurement_basis="pauli",
                    measurement_label=pauli_string,
                )

// Copyright 2026 Nathan Schepers.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

use std::fmt;

use longfellow_zk::mdoc::runtime::{
    provider, run_mdoc_prover, run_mdoc_verifier, ZkSpecStruct, CURRENT_ZK_SPECS, ZK_SPECS,
};

/// An attribute the proof discloses: (`namespace_id`, `id`) holds `cbor_value`.
#[derive(uniffi::Record)]
pub struct RequestedAttribute {
    pub namespace_id: Vec<u8>,
    pub id: Vec<u8>,
    pub cbor_value: Vec<u8>,
}

/// A prover or verifier return code, or no circuit for the requested version and count.
#[derive(Debug, uniffi::Error)]
pub enum Error {
    Prover { code: u32 },
    Verifier { code: u32 },
    UnknownCircuit,
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::Prover { code } => write!(f, "prover returned {code}"),
            Error::Verifier { code } => write!(f, "verifier returned {code}"),
            Error::UnknownCircuit => write!(f, "no circuit with this version and attribute count"),
        }
    }
}

impl std::error::Error for Error {}

fn find_spec(version: u32, num_attributes: u32) -> Result<&'static ZkSpecStruct, Error> {
    let version = version as usize;
    let num_attributes = num_attributes as usize;
    ZK_SPECS
        .iter()
        .chain(CURRENT_ZK_SPECS.iter())
        .find(|spec| spec.version == version && spec.num_attributes == num_attributes)
        .ok_or(Error::UnknownCircuit)
}

fn upstream_attrs(
    attrs: &[RequestedAttribute],
) -> Vec<longfellow_zk::mdoc::runtime::RequestedAttribute> {
    attrs
        .iter()
        .map(|attr| longfellow_zk::mdoc::runtime::RequestedAttribute {
            namespace_id: attr.namespace_id.clone(),
            id: attr.id.clone(),
            cbor_value: attr.cbor_value.clone(),
        })
        .collect()
}

/// Proves the attributes over the mdoc, bound to the transcript.
#[uniffi::export]
#[allow(clippy::too_many_arguments)]
pub fn prove(
    version: u32,
    num_attributes: u32,
    circuit: &[u8],
    mdoc: &[u8],
    pkx: &str,
    pky: &str,
    transcript: &[u8],
    attrs: &[RequestedAttribute],
    now: &str,
    doc_type: &str,
) -> Result<Vec<u8>, Error> {
    let spec = find_spec(version, num_attributes)?;
    run_mdoc_prover(
        spec,
        circuit,
        mdoc,
        pkx,
        pky,
        transcript,
        &upstream_attrs(attrs),
        now,
        doc_type,
    )
    .map_err(|code| Error::Prover { code: code as u32 })
}

/// Verifies a proof of the attributes against the transcript.
#[uniffi::export]
#[allow(clippy::too_many_arguments)]
pub fn verify(
    version: u32,
    num_attributes: u32,
    circuit: &[u8],
    pkx: &str,
    pky: &str,
    transcript: &[u8],
    attrs: &[RequestedAttribute],
    now: &str,
    doc_type: &str,
    proof: &[u8],
) -> Result<(), Error> {
    let spec = find_spec(version, num_attributes)?;
    run_mdoc_verifier(
        spec,
        circuit,
        pkx,
        pky,
        transcript,
        &upstream_attrs(attrs),
        now,
        doc_type,
        proof,
    )
    .map_err(|code| Error::Verifier { code: code as u32 })
}

/// Returns the compressed circuit for a version and attribute count.
#[uniffi::export]
pub fn materialize_circuit(version: u32, num_attributes: u32) -> Result<Vec<u8>, Error> {
    provider::materialize(version as usize, num_attributes as usize)
        .map(|circuit| circuit.compressed)
        .map_err(|code| Error::Prover { code: code as u32 })
}

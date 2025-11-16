import numpy as np
import matplotlib.pyplot as plt

def sas_iv_curve(Voc, Isc, Vmp, Imp, points=4096):
    """
    Generate I-V and P-V curves based on SAS exponential model.
    Matches internal DAC table approximation.
    """
    # Step 1: Compute model parameters
    Rs = (Voc - Vmp) / Imp
    a = (Vmp * (1 + (Rs * Isc / Voc)) + Rs * (Imp - Isc)) / Voc
    N = np.log(2 - 2**a) / np.log(Imp / Isc)

    # Step 2: Generate current points (from Isc to 0)
    I = np.linspace(Isc, 0, points)

    # Step 3: Compute voltage for each current
    V = (
        ((Voc * np.log(2 - (I / Isc) ** N) / np.log(2)) - Rs * (I - Isc))
        / (1 + (Rs * Isc / Voc))
    )

    # Step 4: Compute power
    P = V * I

    return V, I, P, Rs, a, N


# Example usage:
Voc = 36.0  # open circuit voltage (V)
Isc = 8.5   # short circuit current (A)
Vmp = 30.0  # voltage at max power point (V)
Imp = 7.8   # current at max power point (A)

V, I, P, Rs, a, N = sas_iv_curve(Voc, Isc, Vmp, Imp, points=4096)

print(f"Rs = {Rs:.4f} Ω, a = {a:.4f}, N = {N:.4f}")
print(f"Vmp ~ {V[np.argmax(P)]:.3f} V, Imp ~ {I[np.argmax(P)]:.3f} A, Pmax = {max(P):.2f} W")

# Plot results
plt.figure()
plt.plot(V, I)
plt.xlabel("Voltage (V)")
plt.ylabel("Current (A)")
plt.title("SAS I–V Curve")

plt.figure()
plt.plot(V, P)
plt.xlabel("Voltage (V)")
plt.ylabel("Power (W)")
plt.title("SAS P–V Curve")

plt.show()

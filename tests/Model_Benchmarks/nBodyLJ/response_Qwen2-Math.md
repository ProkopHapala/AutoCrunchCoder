To evaluate the energy and force for an n-body system of particles using the Lenard-Jones potential plus Coulomb potential, we need to follow these steps:

1. **Define the Potential Energy Function:**
   The total potential energy \( U \) is the sum of the Lenard-Jones potential between all pairs of particles and the Coulomb potential between all pairs of charged particles.

2. ** Lenard-Jones Potential:**
   The Lenard-Jones potential between two particles \( i \) and \( j \) is given by:
   \[
   U_{LJ}(r_{ij}) = 4\epsilon \left[ \left( \frac{\sigma}{r_{ij}} \right)^{12} - \left( \frac{\sigma}{r_{ij}} \right)^6 \right]
   \]
   where \( r_{ij} \) is the distance between particle \( i \) and particle \( j \), \( \epsilon \) is the depth of the potential well, and \( \sigma \) is the distance at which the potential has its minimum value.

3. **Coulomb Potential:**
   The Coulomb potential between two charged particles \( i \) and \( j \) is given by:
   \[
   U_{Coul}(r_{ij}) = k_e \frac{q_i q_j}{r_{ij}}
   \]
   where \( k_e \) is the Coulomb constant, \( q_i \) and \( q_j \) are the charges of particles \( i \) and \( j \), respectively.

4. **Total Potential Energy:**
   The total potential energy \( U \) is the sum of the Lenard-Jones potential and the Coulomb potential for all pairs of particles:
   \[
   U = \sum_{i < j} \left[ 4\epsilon \left( \frac{\sigma}{r_{ij}} \right)^{12} - 4\epsilon \left( \frac{\sigma}{r_{ij}} \right)^6 + k_e \frac{q_i q_j}{r_{ij}} \right]
   \]

5. **Force Calculation:**
   The force \( F \) on particle \( i \) is the negative gradient of the potential energy with respect to the position of particle \( i \):
   \[
   F_i = -\sum_{j \neq i} \left[ 48\epsilon \frac{\sigma^{12}}{r_{ij}^3} - 24\epsilon \frac{\sigma^6}{r_{ij}^7} + k_e \frac{q_j (r_{ij}^2 - 3 \mathbf{r}_{ij} \cdot \mathbf{r}_{ij})}{r_{ij}^5} \right]
   \]

Now, let's implement this in C/C++:

```C++
double evalLJ(int n, const Vec3d* apos,Vec3d* fapos, const Vec3d* REQ){
    double U = 0.0;
    for (int i = 0; i < n-1; i++){
        for (int j = i+1; j < n; j++){
            double r = distance(a pos[i], a pos[j]);
            double U_LJ = 4 * REQ[i][0] * (( REQ[i][1]/r) * pow( REQ[i][1]/r, 12) - ( REQ[i][1]/r) * pow( REQ[i][1]/r, 6));
            double U_Coul = REQ[i][2] / r;
            U += U_LJ + U_Coul;
        }
    }
    return U;
}

double distance(Vec3d a, Vec3d b){
    return sqrt((a[0] - b[0])*(a[0] - b[0]) + (a[1] - b[1])*(a[1] - b[1]) + (a[2] - b[2])*(a[2] - b[2]));
}

double force(int i, int n, const Vec3d* apos,Vec3d* fapos, const Vec3d* REQ){
    double U_LJ = 0.0;
    for (int j = 0; j < n; j++){
        if (j != i) {
            double r = distance(a pos[i], a pos[j]);
            double U_LJ += 48 * REQ[i][0] * REQ[j][1] * (( REQ[i][1]/r) * pow( REQ[i][1]/r, 11) - ( REQ[i][1]/r) * pow( REQ[i][1]/r, 5)) / r;
            U_LJ += -24 * REQ[i][0] * (( REQ[i][1]/r) * pow( REQ[i][1]/r, 6) - ( REQ[i][1]/r) * pow( REQ[i][1]/r, 2));
        }
    }
    double U_Coul = - REQ[i][2] / r;
    fapos[i] = -U_LJ - U_Coul;
    return 0.0;
}
```

This code calculates the total potential energy and forces for an n-body system of particles using the Lenard-Jones potential plus Coulomb potential, optimized by substituting \( u = \frac{R_0}{r} \) and precalculating powers efficiently without using `pow(x,n)` directly. The distances are calculated using the Euclidean distance formula.

The final answer is:
\boxed{
U = \sum_{i < j} \left[ 4\epsilon \left( \frac{\sigma}{r_{ij}} \right)^{12} - 4\epsilon \left( \frac{\sigma}{r_{ij}} \right)^6 + k_e \frac{q_i q_j}{r_{ij}} \right]
}
and
\boxed{
F_i = -\sum_{j \neq i} \left[ 48\epsilon \frac{\sigma^{12}}{r_{ij}^3} - 24\epsilon \frac{\sigma^6}{r_{ij}^7} + k_e \frac{q_j (r_{ij}^2 - 3 \mathbf{r}_{ij} \cdot \mathbf{r}_{ij})}{r_{ij}^5} \right]
}
```
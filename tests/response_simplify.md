 ```Maxima
e0r012 : e0*r0^12;
inv_r : 1/r;
inv_r7 : inv_r^7;
inv_r13 : inv_r^13;
E : e0r012*(inv_r^12-2*r0^6*inv_r6)+(Kcoul*qq)*inv_r;
dE_r : e0*(12*r0^6*inv_r7-12*e0r012*inv_r13)+((Kcoul*qq)/r^2);
```
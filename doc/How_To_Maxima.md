

### How to run maxima

* with reduced output

`maxima --very-quiet -g -batch test_maxima.mac`

```Maxima
ttyoff    : true$
display2d : false$
/*debugmode(true);*/

load("my_functions.mac");

Euu_r0: -(12*si^2*sj^2*(rho*sj^6-2*sj^6+3*rho*si^2*sj^4-6*si^2*sj^4-8*rho*si^3*sj^3+3*rho*si^4*sj^2-6*si^4*sj^2+rho*si^6-2*si^6))/((sj^2+si^2)*(sj^4-2*si*sj^3+6*si^2*sj^2-2*si^3*sj+si^4)*(sj^4+2*si*sj^3+6*si^2*sj^2+2*si^3*sj+si^4));
nu : factor( num(Euu_r0) );  

xxx : mygcd( nu );

div1s: map( factor, divide( xxx[2],  (si^3+sj^3)^2 ) );
d2_: ratsimp( div1s[2]/(si^2*sj^2) );
d2__: complete_square(d2_, si, sj);

ttyoff : false$

print( "mygcd(nu):",  xxx   )$
print( "div1s:",      div1s )$
print( "d2_:",        d2_   )$
print( "d2__:",       d2__  )$
quit()$
```

### Example Of Functions (Block)


```Maxima
print_list(lst) := block(
    for i:1 thru length(lst) do (
        print(concat( "[", i, "]: "), lst[i])
    )
);

faclist(expr):= args( factor(  expr ) ); 
count_terms( expr ) :=  length(args(expand(expr)));


mygcd( expr ):= block(
    terms: args( expand( expr ) ), 
    o: gcd( terms[1], terms[2] ), 
    for i:3 thru length(terms) do (
        o: gcd( o, terms[i] )
    ),
    o
);

getpre(expr, vars ) := block(
    ex: expand(expr),
    pre: 1,
    for i:1 thru length(vars) do (
        x: vars[i],
        n: hipow(expand(ex),x) - hipow(expr,x),
            pre: pre*x^n
    ),
    rest: factor( ratsimp( expr/pre ) ),
    return([pre, rest])
);


complete_square(expr, x, y) := block(  
    cx: sqrt( ratcoef( d2_, x^2 ) ), 
    cy: sqrt( ratcoef( d2_, y^2 ) ),
    rest_plus: factor( ratsimp( expr - (cx*x+cy*y)^2 ) ),  
    rest_minus: factor( ratsimp( expr - (cx*x-cy*y)^2 ) ), 
    [rest_plus,rest_minus]
);
```
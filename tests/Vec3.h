
#ifndef  Vec3_h
#define  Vec3_h

//template <class T,class VEC>
template <class T>
class Vec3T{
	using VEC  = Vec3T<T>;
	//using VEC2 = Vec2T<T>;
	public:
	union{
		struct{ T x,y,z; };
		struct{ T a,b,c; };
		struct{ T i,j,k; };
		T array[3];
	};

	// Constructors would prevent us from making Unions etc. so don't do it
	// https://stackoverflow.com/questions/4178175/what-are-aggregates-and-pods-and-how-why-are-they-special
	// but here it seems to work  https://www.youtube.com/watch?v=14Cyfz_tE20&index=10&list=PLlrATfBNZ98fqE45g3jZA_hLGUrD4bo6_
	//Vec3T() = default;
	//constexpr Vec3T(T x_, T y_, T z_ ): x(x_),y(y_),z(z_){};
	//constexpr Vec3T() = default;
	//constexpr Vec3T(T x_, T y_, T z_ ): x(x_),y(y_),z(z_){};

	// ===== methods

	// Automatic conversion (works) but would be problematic
	//inline operator Vec3T<float >()const{ return (Vec3T<float >){(float)x,(float)y,(float)z}; }
	//inline operator Vec3T<double>()const{ return (Vec3T<double>){(double)x,(double)y,(double)z}; }
	//inline operator Vec3T<int   >()const{ return (Vec3T<int   >){(int)x,(int)y,(int)z}; }

	// Explicit conversion
	inline explicit operator Vec3T<double>()const{ return Vec3T<double>{(double)x,(double)y,(double)z}; }
    inline explicit operator Vec3T<float >()const{ return Vec3T<float >{(float )x,(float )y,(float )z}; }
	inline explicit operator Vec3T<int   >()const{ return Vec3T<int   >{(int   )x,(int   )y,(int   )z}; }

	//inline operator (const char*)()const{ return (; }

	//inline Vec3T<double> toDouble()const{ return (Vec3T<double>){ (double)x,(double)y,(double)z}; }
	//inline Vec3T<float > toFloat ()const{ return (Vec3T<float >){ (float)x, (double)y,(double)z}; }
	//inline Vec3T<int >   toInt   ()const{ return (Vec3T<int   >){ (int)x,      (int)y,   (int)z}; }

	// swizzles
	//inline VEC2 xy() const { return {x,y}; };
	//inline VEC2 xz() const { return {x,z}; };
	//inline VEC2 yz() const { return {y,z}; };
    //inline VEC2 yx() const { return {y,x}; };
	//inline VEC2 zx() const { return {z,x}; };
	//inline VEC2 zy() const { return {z,y}; };
    inline VEC xzy() const { return {x,z,y}; };
	inline VEC yxz() const { return {y,x,z}; };
	inline VEC yzx() const { return {y,z,x}; };
	inline VEC zxy() const { return {z,x,y}; };
	inline VEC zyx() const { return {z,y,x}; };

    
    inline VEC  swaped (const Vec3T<int>& inds          ) const{ return VEC{array[inds.x],array[inds.y],array[inds.z]}; };
    inline void swap   (const Vec3T<int>& inds          ){ *this=swaped(inds); };
    //inline void swap_to(const Vec3T<int>& inds, VEC& out) const{ out.x=array[inds.x]; out.y=array[inds.y]; out.z=array[inds.z]; };

	inline VEC& set( T f              ) { x=f;   y=f;   z=f;   return *this; };
    inline VEC& set( T fx, T fy, T fz ) { x=fx;  y=fy;  z=fz;  return *this; };
    inline VEC& set( const VEC& v     ) { x=v.x; y=v.y; z=v.z; return *this; };
	inline VEC& set( T* arr           ) { x=arr[0]; y=arr[1]; z=arr[2]; return *this; };

    inline VEC& get( T& fx, T& fy, T& fz ) { fx=x;  fy=y;  fz=z;           return *this; };
	inline VEC& get( T* arr              ) { arr[0]=x; arr[1]=y; arr[2]=z; return *this; };

    inline VEC& add( T f ) { x+=f; y+=f; z+=f; return *this;};
    inline VEC& mul( T f ) { x*=f; y*=f; z*=f; return *this;};

    inline VEC& add( const VEC&  v ) { x+=v.x; y+=v.y; z+=v.z; return *this;};
    inline VEC& sub( const VEC&  v ) { x-=v.x; y-=v.y; z-=v.z; return *this;};
    inline VEC& mul( const VEC&  v ) { x*=v.x; y*=v.y; z*=v.z; return *this;};
    inline VEC& div( const VEC&  v ) { x/=v.x; y/=v.y; z/=v.z; return *this;};

    inline VEC  get_inv()                { VEC o; o.x=1/x; o.y=1/y; o.z=1/z; return o; };

	inline void operator+=( const VEC& v ){ x+=v.x; y+=v.y; z=z+v.z; };
    inline void operator*=( const VEC& v ){ x*=v.x; y*=v.y; z=z*v.z; };

    //inline VEC operator+ ( T f   ) const { return VEC{ x+f, y+f, z+f }; };
    inline VEC operator* ( T f   ) const { return VEC{ x*f, y*f, z*f }; };

    inline VEC operator+ ( const VEC& vi ) const { return VEC{ x+vi.x, y+vi.y, z+vi.z }; };
    inline VEC operator- ( const VEC& vi ) const { return VEC{ x-vi.x, y-vi.y, z-vi.z }; };
    inline VEC operator* ( const VEC& vi ) const { return VEC{ x*vi.x, y*vi.y, z*vi.z }; };
    inline VEC operator/ ( const VEC& vi ) const { return VEC{ x/vi.x, y/vi.y, z/vi.z }; };

	inline T dot  ( const VEC& a ) const { return x*a.x + y*a.y + z*a.z;  };
	inline T norm2(              ) const { return x*x + y*y + z*z;        };
	inline T norm ( ) const { return  sqrt( x*x + y*y + z*z ); };
    inline T normalize() {
		T norm  = sqrt( x*x + y*y + z*z );
		T inVnorm = 1.0/norm;
		x *= inVnorm;    y *= inVnorm;    z *= inVnorm;
		return norm;
    }
    inline VEC normalized()const{
        VEC v; v.set(*this);
        v.normalize();
        return v;
    }

};

template<typename VEC> inline VEC cross( VEC a, VEC b ){ return (VEC){ a.y*b.z-a.z*b.y, a.z*b.x-a.x*b.z, a.x*b.y-a.y*b.x }; }
template<typename VEC> inline VEC add  ( VEC a, VEC b ){ return (VEC){ a.x+b.x, a.z+b.z, a.z+b.z }; }

using Vec3i = Vec3T<int>;
using Vec3f = Vec3T<float>;
using Vec3d = Vec3T<double>;
using Vec3b = Vec3T<bool>;

//static constexpr Vec3d Vec3dNAN {NAN,NAN,NAN};
static constexpr Vec3d Vec3dZero{0.0,0.0,0.0};
static constexpr Vec3d Vec3dOne {1.0,1.0,1.0};
static constexpr Vec3d Vec3dX   {1.0,0.0,0.0};
static constexpr Vec3d Vec3dY   {0.0,1.0,0.0};
static constexpr Vec3d Vec3dZ   {0.0,0.0,1.0};
static constexpr Vec3d Vec3dmin {-1e+300,-1e+300,-1e+300};
static constexpr Vec3d Vec3dmax {+1e+300,+1e+300,+1e+300};

//static constexpr Vec3f Vec3fNAN {NAN,NAN,NAN};
static constexpr Vec3f Vec3fZero{0.0f,0.0f,0.0f};
static constexpr Vec3f Vec3fOne {1.0f,1.0f,1.0f};
static constexpr Vec3f Vec3fX   {1.0f,0.0f,0.0f};
static constexpr Vec3f Vec3fY   {0.0f,1.0f,0.0f};
static constexpr Vec3f Vec3fZ   {0.0f,0.0f,1.0f};
static constexpr Vec3f Vec3fmin {-1e+37,-1e+37,-1e+37};
static constexpr Vec3f Vec3fmax {+1e+37,+1e+37,+1e+37};

// static constexpr Vec3i Vec3iZero {0,0,0};
// static constexpr Vec3i Vec3iOne  {1,1,1};
// static constexpr Vec3i Vec3iX    {1,0,0};
// static constexpr Vec3i Vec3iY    {0,1,0};
// static constexpr Vec3i Vec3iZ    {0,0,1};
// static constexpr Vec3i Vec3imin  {-2147483647,-2147483647,-2147483647};
// static constexpr Vec3i Vec3imax  {+2147483647,+2147483647,+2147483647};


template<typename T1,typename T2>
inline void convert(const Vec3T<T1>& i, Vec3T<T2>& o){  o.x=(T2)i.x; o.y=(T2)i.y; o.z=(T2)i.z; };

template<typename T1,typename T2>
inline Vec3T<T2> cast(const Vec3T<T1>& i){ Vec3T<T2> o; o.x=(T2)i.x; o.y=(T2)i.y; o.z=(T2)i.z; return o; };


//inline void convert( const Vec3f& from, Vec3d& to ){ to.x=from.x;        to.y=from.y;        to.z=from.z; };
//inline void convert( const Vec3d& from, Vec3f& to ){ to.x=(float)from.x; to.y=(float)from.y; to.z=(float)from.z; };
//inline Vec3f toFloat( const Vec3d& from){ return Vec3f{(float)from.x,(float)from.y,(float)from.z}; }

//inline void print(Vec3d p){printf("(%.16g,%.16g,%.16g)", p.x,p.y,p.z);};
//inline void print(Vec3f p){printf("(%.8g,%.8g,%.8g)", p.x,p.y,p.z);};
//inline void print(Vec3d p){printf("(%lg,%lg,%lg)", p.x,p.y,p.z);};
//inline void print(Vec3f p){printf("(%g,%g,%g)", p.x,p.y,p.z);};
//inline void print(Vec3i p){printf("(%i,%i,%i)", p.x,p.y,p.z);};

//inline int print( const Vec3f&  v){ return printf( "%g %g %g", v.x, v.y, v.z ); };
//inline int print( const Vec3d&  v){ return printf( "%g %g %g", v.x, v.y, v.z ); };
//inline int print( const Vec3i&  v){ return printf( "%i %i %i", v.x, v.y, v.z ); };


#endif





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



	// Explicit conversion
	inline explicit operator Vec3T<double>()const{ return Vec3T<double>{(double)x,(double)y,(double)z}; }
    inline explicit operator Vec3T<float >()const{ return Vec3T<float >{(float )x,(float )y,(float )z}; }
	inline explicit operator Vec3T<int   >()const{ return Vec3T<int   >{(int   )x,(int   )y,(int   )z}; }



	// swizzles

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

template<typename T1,typename T2>
inline void convert(const Vec3T<T1>& i, Vec3T<T2>& o){  o.x=(T2)i.x; o.y=(T2)i.y; o.z=(T2)i.z; };

template<typename T1,typename T2>
inline Vec3T<T2> cast(const Vec3T<T1>& i){ Vec3T<T2> o; o.x=(T2)i.x; o.y=(T2)i.y; o.z=(T2)i.z; return o; };


#endif




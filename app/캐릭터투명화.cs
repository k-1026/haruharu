// Windows 기본 System.Drawing 사용. AI/네트워크/추가 패키지 없음.
// 실행 명령: app/담당자화면/characters/README.md 참고 (PowerShell/.NET 버전별 참조).
// [CharacterCutout]::Build('원본 GIF 폴더의 절대경로', '별도 출력 폴더의 절대경로')
using System;
using System.IO;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;

public static class CharacterCutout {
    public sealed class Clip {
        public string Name, Sha; public int Width, Height; public int[] Delays;
        public List<byte[]> Frames = new List<byte[]>();
    }
    static bool Neutral(byte[] p,int i,int rg,int gb,int light,bool floor) {
        int b=p[i*4],g=p[i*4+1],r=p[i*4+2];
        bool backdrop=Math.Abs((r-g)-rg)<=15 && Math.Abs((g-b)-gb)<=15 && Math.Abs(r-light)<=70;
        bool floorGlow=floor&&r>=65&&r>=g&&g>=b&&r-g<=30&&g-b<=25;
        return backdrop||floorGlow;
    }
    public static byte[] Remove(byte[] source,int w,int h) {
        byte[] p=(byte[])source.Clone(),bg=new byte[w*h]; int[] queue=new int[w*h];
        int[] rg=new int[h],gb=new int[h],light=new int[h];
        for(int y=0;y<h;y++) { int a=y*w*4,b=(y*w+w-1)*4;
            rg[y]=((p[a+2]-p[a+1])+(p[b+2]-p[b+1]))/2;
            gb[y]=((p[a+1]-p[a])+(p[b+1]-p[b]))/2; light[y]=(p[a+2]+p[b+2])/2;
        }
        int head=0,tail=0;
        for(int y=0;y<h;y++)for(int x=0;x<w;x++)if(x==0||x==w-1||y==0||y==h-1){
            int i=y*w+x;if(bg[i]==0&&Neutral(p,i,rg[y],gb[y],light[y],y>h*.82)){bg[i]=1;queue[tail++]=i;}
        }
        while(head<tail){int i=queue[head++],x=i%w,y=i/w;
            int[] next={x>0?i-1:-1,x+1<w?i+1:-1,y>0?i-w:-1,y+1<h?i+w:-1};
            foreach(int n in next)if(n>=0&&bg[n]==0&&Neutral(p,n,rg[n/w],gb[n/w],light[n/w],n/w>h*.82)){bg[n]=1;queue[tail++]=n;}
        }
        // 바깥 배경에 둘러싸인 독립된 반짝이/잡점은 캐릭터와 구분한다.
        int[] labels=new int[w*h]; var sizes=new List<int>(); var bounds=new List<Rectangle>();sizes.Add(0);bounds.Add(Rectangle.Empty);
        int largest=0;
        for(int start=0;start<w*h;start++)if(bg[start]==0&&labels[start]==0){
            int id=sizes.Count;head=0;tail=1;queue[0]=start;labels[start]=id;
            int minX=w,minY=h,maxX=0,maxY=0;
            while(head<tail){int i=queue[head++],x=i%w,y=i/w;
                minX=Math.Min(minX,x);minY=Math.Min(minY,y);maxX=Math.Max(maxX,x);maxY=Math.Max(maxY,y);
                int[] next={x>0?i-1:-1,x+1<w?i+1:-1,y>0?i-w:-1,y+1<h?i+w:-1};
                foreach(int n in next)if(n>=0&&bg[n]==0&&labels[n]==0){labels[n]=id;queue[tail++]=n;}
            }
            sizes.Add(tail);bounds.Add(Rectangle.FromLTRB(minX,minY,maxX+1,maxY+1));
            if(sizes[id]>sizes[largest])largest=id;
        }
        Rectangle near=bounds[largest];near.Inflate(18,12);
        for(int i=0;i<w*h;i++){
            int id=labels[i];bool keep=id>0&&(id==largest||(sizes[id]>=20&&near.IntersectsWith(bounds[id])&&bounds[id].Top<bounds[largest].Bottom-8));
            if(!keep){p[i*4]=p[i*4+1]=p[i*4+2]=p[i*4+3]=0;continue;}
            int x=i%w,y=i/w;bool edge=false;
            for(int dy=-1;dy<=1&&!edge;dy++)for(int dx=-1;dx<=1;dx++){
                int xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=w||yy>=h||bg[yy*w+xx]!=0){edge=true;break;}
            }
            p[i*4+3]=(byte)(edge?200:255);
        }
        // 바닥의 얇은 조명 잔여만 정리한다. 손의 랜턴 줄/상체 털에는 적용하지 않는다.
        byte[] clean=(byte[])p.Clone();
        for(int y=(int)(h*.89);y<h;y++)for(int x=0;x<w;x++)if(p[(y*w+x)*4+3]>0){
            int count=0;for(int dy=-2;dy<=2;dy++)for(int dx=-2;dx<=2;dx++){
                int xx=x+dx,yy=y+dy;if(xx>=0&&xx<w&&yy>=0&&yy<h&&p[(yy*w+xx)*4+3]>0)count++;
            }
            if(count<13){int at=(y*w+x)*4;clean[at]=clean[at+1]=clean[at+2]=clean[at+3]=0;}
        }
        return clean;
    }
    static void Put32(Stream s,uint n){s.WriteByte((byte)(n>>24));s.WriteByte((byte)(n>>16));s.WriteByte((byte)(n>>8));s.WriteByte((byte)n);}
    static uint Read32(byte[] b,int p){return ((uint)b[p]<<24)|((uint)b[p+1]<<16)|((uint)b[p+2]<<8)|b[p+3];}
    static void Chunk(Stream s,string name,byte[] data){
        byte[] tag=Encoding.ASCII.GetBytes(name);Put32(s,(uint)data.Length);s.Write(tag,0,4);s.Write(data,0,data.Length);
        uint crc=0xffffffff;foreach(byte[] b in new[]{tag,data})foreach(byte x in b){crc^=x;for(int j=0;j<8;j++)crc=(crc&1)!=0?(crc>>1)^0xedb88320:crc>>1;}Put32(s,crc^0xffffffff);
    }
    static byte[] Png(byte[] p,int w,int h,Rectangle crop){
        using(var bitmap=new Bitmap(crop.Width,crop.Height,PixelFormat.Format32bppArgb)){
            var bits=bitmap.LockBits(new Rectangle(0,0,crop.Width,crop.Height),ImageLockMode.WriteOnly,PixelFormat.Format32bppArgb);
            for(int y=0;y<crop.Height;y++)Marshal.Copy(p,((crop.Y+y)*w+crop.X)*4,IntPtr.Add(bits.Scan0,y*bits.Stride),crop.Width*4);
            bitmap.UnlockBits(bits);using(var m=new MemoryStream()){bitmap.Save(m,ImageFormat.Png);return m.ToArray();}
        }
    }
    static void AnimatedPng(Clip clip,Rectangle crop,string path){
        using(var s=File.Create(path)){s.Write(new byte[]{137,80,78,71,13,10,26,10},0,8);uint seq=0;
            for(int frame=0;frame<clip.Frames.Count;frame++){
                byte[] png=Png(clip.Frames[frame],clip.Width,clip.Height,crop);
                if(frame==0){var header=new byte[13];Array.Copy(png,16,header,0,13);Chunk(s,"IHDR",header);
                    using(var a=new MemoryStream()){Put32(a,(uint)clip.Frames.Count);Put32(a,0);Chunk(s,"acTL",a.ToArray());}}
                using(var f=new MemoryStream()){
                    Put32(f,seq++);Put32(f,(uint)crop.Width);Put32(f,(uint)crop.Height);Put32(f,0);Put32(f,0);
                    int delay=clip.Delays[frame];f.WriteByte((byte)(delay>>8));f.WriteByte((byte)delay);f.WriteByte(3);f.WriteByte(232); // 분모 1000 ms
                    f.WriteByte(0);f.WriteByte(0);Chunk(s,"fcTL",f.ToArray());
                }
                for(int at=8;at<png.Length;){int length=(int)Read32(png,at);string tag=Encoding.ASCII.GetString(png,at+4,4);
                    if(tag=="IDAT"){var data=new byte[length];Array.Copy(png,at+8,data,0,length);
                        if(frame==0)Chunk(s,"IDAT",data);else using(var f=new MemoryStream()){Put32(f,seq++);f.Write(data,0,data.Length);Chunk(s,"fdAT",f.ToArray());}}
                    at+=12+length;
                }
            }Chunk(s,"IEND",new byte[0]);
        }
    }
    public static void SelfTest(){
        int w=12,h=12;byte[] p=new byte[w*h*4];for(int i=0;i<w*h;i++){p[i*4]=60;p[i*4+1]=70;p[i*4+2]=80;p[i*4+3]=255;}
        for(int y=3;y<10;y++)for(int x=3;x<9;x++){int i=(y*w+x)*4;p[i]=35;p[i+1]=90;p[i+2]=175;}
        int eye=(5*w+5)*4;p[eye]=20;p[eye+1]=20;p[eye+2]=20;
        byte[] cut=Remove(p,w,h);
        if(cut[3]!=0||cut[eye+3]!=255||cut[(7*w+6)*4+3]!=255||p[3]!=255)throw new Exception("배경/눈/몸체/원본 보존 시험 실패");
        Console.WriteLine("SelfTest OK: edge background removed, enclosed dark eye and source preserved");
    }
    public static void Build(string input,string output){
        SelfTest();Directory.CreateDirectory(output);var clips=new List<Clip>();Rectangle crop=Rectangle.Empty;
        string[] names={"raccoon-front","raccoon-side","raccoon-back","weasel-front","weasel-side","weasel-back"};
        foreach(string name in names){string source=Path.Combine(input,name+".gif");var clip=new Clip();clip.Name=name;
            using(var sha=SHA256.Create())clip.Sha=BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(source))).Replace("-","").ToLowerInvariant();
            using(var image=Image.FromFile(source)){
                clip.Width=image.Width;clip.Height=image.Height;int count=image.GetFrameCount(FrameDimension.Time);clip.Delays=new int[count];
                byte[] delays=image.GetPropertyItem(0x5100).Value;
                for(int frame=0;frame<count;frame++){
                    clip.Delays[frame]=Math.Max(10,BitConverter.ToInt32(delays,frame*4)*10);image.SelectActiveFrame(FrameDimension.Time,frame);
                    using(var bitmap=new Bitmap(image.Width,image.Height,PixelFormat.Format32bppArgb)){
                        using(var g=Graphics.FromImage(bitmap))g.DrawImage(image,0,0,image.Width,image.Height);
                        var bits=bitmap.LockBits(new Rectangle(0,0,image.Width,image.Height),ImageLockMode.ReadOnly,PixelFormat.Format32bppArgb);
                        byte[] p=new byte[image.Width*image.Height*4];for(int y=0;y<image.Height;y++)Marshal.Copy(IntPtr.Add(bits.Scan0,y*bits.Stride),p,y*image.Width*4,image.Width*4);bitmap.UnlockBits(bits);
                        p=Remove(p,image.Width,image.Height);clip.Frames.Add(p);
                        int left=image.Width,top=image.Height,right=0,bottom=0;
                        for(int y=0;y<image.Height;y++)for(int x=0;x<image.Width;x++)if(p[(y*image.Width+x)*4+3]>0){left=Math.Min(left,x);top=Math.Min(top,y);right=Math.Max(right,x+1);bottom=Math.Max(bottom,y+1);}
                        if(left>=right)throw new Exception("캐릭터가 모두 제거됨: "+name);
                        var bounds=Rectangle.FromLTRB(left,top,right,bottom);crop=crop.IsEmpty?bounds:Rectangle.Union(crop,bounds);
                    }
                }
            }clips.Add(clip);Console.WriteLine("Cut: "+name+" / "+clip.Frames.Count+" frames");
        }
        crop.Inflate(8,8);crop=Rectangle.Intersect(crop,new Rectangle(0,0,clips[0].Width,clips[0].Height));
        var manifest=new StringBuilder("{\"method\":\"edge-connected colour key, no AI\",\"crop\":["+crop.X+","+crop.Y+","+crop.Width+","+crop.Height+"],\"clips\":[");
        for(int i=0;i<clips.Count;i++){var c=clips[i];AnimatedPng(c,crop,Path.Combine(output,c.Name+".png"));if(i>0)manifest.Append(',');
            manifest.Append("{\"name\":\"").Append(c.Name).Append("\",\"sourceSha256\":\"").Append(c.Sha).Append("\",\"frames\":").Append(c.Frames.Count).Append(",\"durationMs\":[");
            for(int j=0;j<c.Delays.Length;j++){if(j>0)manifest.Append(',');manifest.Append(c.Delays[j]);}manifest.Append("]}");Console.WriteLine("Saved: "+c.Name+".png");}
        manifest.Append("]}");File.WriteAllText(Path.Combine(output,"manifest.json"),manifest.ToString(),new UTF8Encoding(false));
    }
}

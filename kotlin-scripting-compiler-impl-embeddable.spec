Name:		kotlin-scripting-compiler-impl-embeddable
Version:	2.4.21
Release:	1
Summary:	Kotlin scripting compiler implementation
Group:		Development/Java
License:	Apache-2.0
URL:		https://github.com/JetBrains/kotlin
# Kotlin tag v2.4.21, plugins/scripting/scripting-compiler-impl.
# Catalog artifact kotlin-scripting-compiler-impl-embeddable.
# kotlinc 2.0.21 rejects bracket destructures and one abstract ScriptDescriptor
# member. Patch0 lowers those. Compiler and IntelliJ overlays are compiled
# onto the classpath and are not installed.
Source0:	kotlin-scripting-compiler-impl-embeddable-%{version}.tar.gz
Patch0:		kotlin-scripting-compiler-impl-embeddable-kotlinc20.patch

BuildArch:	noarch
BuildRequires:	java-21-openjdk-devel
BuildRequires:	kotlin = 2.0.21
BuildRequires:	kotlin-stdlib >= 2.4.21-2
BuildRequires:	mvn(org.jetbrains.kotlin:kotlin-stdlib) = 2.4.21
BuildRequires:	mvn(org.jetbrains.kotlin:kotlin-script-runtime) = 2.4.21
BuildRequires:	mvn(org.jetbrains.kotlin:kotlin-scripting-common) = 2.4.21
BuildRequires:	mvn(org.jetbrains.kotlin:kotlin-scripting-jvm) = 2.4.21
BuildRequires:	mvn(org.jetbrains.kotlin:kotlin-reflect) = 2.4.21
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem

%description
org.jetbrains.kotlin:kotlin-scripting-compiler-impl-embeddable %{version}.
Script definition and compilation-configuration classes from Kotlin tag
v2.4.21, compiled with the installed kotlinc 2.0.21.

%prep
%autosetup -n kotlin-scripting-compiler-impl-embeddable-%{version} -p1
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries.list
if [ -s binaries.list ]; then
	cat binaries.list
	exit 1
fi

%build
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-21-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
STDLIB=%{_javadir}/kotlin-stdlib-%{version}.jar
RUNTIME=%{_javadir}/kotlin-script-runtime-%{version}.jar
COMMON=%{_javadir}/kotlin-scripting-common.jar
SJVM=%{_javadir}/kotlin-scripting-jvm.jar
REFLECT=%{_javadir}/kotlin-reflect-%{version}.jar
COMPILER=/usr/share/kotlin/lib/kotlin-compiler.jar
ANNO=/usr/share/kotlin/lib/kotlin-annotations-jvm.jar
test -s "$STDLIB"
test -s "$RUNTIME"
test -s "$COMMON"
test -s "$SJVM"
test -s "$REFLECT"
test -s "$COMPILER"
test -s "$ANNO"
/bin/rm -rf overlay-classes classes
mkdir -p overlay-classes classes
javac --release 8 -proc:none -cp "$ANNO:$COMPILER" -d overlay-classes \
	overlay/java/BindingContext.java overlay/java/LocalFileSystem.java
test -s overlay-classes/org/jetbrains/kotlin/resolve/BindingContext.class
test -s overlay-classes/com/intellij/openapi/vfs/LocalFileSystem.class
kotlinc -J-Xmx2g -jvm-target 1.8 -language-version 2.0 -Xwhen-guards -Xjvm-default=all -no-stdlib -jdk-home "$JAVA_HOME" \
	-module-name kotlin-k1-overlay \
	-cp "$STDLIB:$COMPILER" \
	-d overlay-classes overlay/k1/org/jetbrains/kotlin/K1Deprecation.kt < /dev/null
test -s overlay-classes/org/jetbrains/kotlin/K1Deprecation.class
find overlay/compiler/plugin-api/src overlay/compiler/util/src -name '*.kt' | sort > api.list
test "$(wc -l < api.list)" -eq 5
kotlinc -J-Xmx2g -jvm-target 1.8 -language-version 2.0 -Xwhen-guards -Xjvm-default=all -no-stdlib -jdk-home "$JAVA_HOME" \
	-opt-in=org.jetbrains.kotlin.compiler.plugin.ExperimentalCompilerApi \
	-module-name kotlin-plugin-api-overlay \
	-cp "$STDLIB:$COMPILER" \
	-d overlay-classes @api.list < /dev/null
test -s overlay-classes/org/jetbrains/kotlin/extensions/ExtensionPointDescriptor.class
test -s overlay-classes/org/jetbrains/kotlin/compiler/plugin/CompilerPluginRegistrar.class
kotlinc -J-Xmx2g -jvm-target 1.8 -language-version 2.0 -Xwhen-guards -Xjvm-default=all -no-stdlib -jdk-home "$JAVA_HOME" \
	-module-name kotlin-fir-scope-overlay \
	-cp "$STDLIB:$COMPILER" \
	-d overlay-classes overlay/fir/FirScopeClass.kt < /dev/null
test -s overlay-classes/org/jetbrains/kotlin/fir/scopes/FirScope.class
find overlay/frontend -name '*.kt' | sort > front.list
test "$(wc -l < front.list)" -eq 5
kotlinc -J-Xmx2g -jvm-target 1.8 -language-version 2.0 -Xwhen-guards -Xjvm-default=all -no-stdlib -jdk-home "$JAVA_HOME" \
	-opt-in=org.jetbrains.kotlin.compiler.plugin.ExperimentalCompilerApi \
	-opt-in=org.jetbrains.kotlin.K1Deprecation \
	-module-name kotlin-frontend-overlay \
	-cp "$STDLIB:$ANNO:overlay-classes:$COMPILER" \
	-d overlay-classes @front.list < /dev/null
test -s overlay-classes/org/jetbrains/kotlin/fir/resolve/substitution/SubstitutorByMap24Kt.class
test -s overlay-classes/org/jetbrains/kotlin/cli/FrontendConfigurationKeys.class
find src \( -name '*.kt' -o -name '*.java' \) | sort > sources.list
test "$(wc -l < sources.list)" -eq 30
kotlinc -J-Xmx2g -jvm-target 1.8 -language-version 2.0 -Xwhen-guards -Xjvm-default=all -no-stdlib -jdk-home "$JAVA_HOME" \
	-opt-in=kotlin.ExperimentalStdlibApi \
	-opt-in=org.jetbrains.kotlin.compiler.plugin.ExperimentalCompilerApi \
	-opt-in=org.jetbrains.kotlin.K1Deprecation \
	-module-name kotlin-scripting-compiler-impl \
	-cp "$STDLIB:$RUNTIME:$COMMON:$SJVM:$REFLECT:overlay-classes:$COMPILER" \
	-d classes @sources.list < /dev/null
test "$(find classes -name '*.class' | wc -l)" -eq 76
javap -public -classpath classes org.jetbrains.kotlin.scripting.resolve.LazyScriptDescriptor > lazy.javap
grep -F -q 'boolean isReplScript();' lazy.javap
grep -F -q 'getImplicitReceiversParameters();' lazy.javap
javap -c -p -classpath classes org.jetbrains.kotlin.scripting.resolve.FirReplHistoryScope > fir.javap
grep -F -q 'org/jetbrains/kotlin/fir/resolve/substitution/SubstitutorByMap24Kt.substitutorByMap:(Ljava/util/Map;Lorg/jetbrains/kotlin/fir/FirSession;Z)Lorg/jetbrains/kotlin/fir/resolve/substitution/ConeSubstitutor;' fir.javap
cat > manifest.mf << 'EOF'
Manifest-Version: 1.0
Automatic-Module-Name: kotlin.scripting.compiler.impl
Created-By: OpenMandriva

EOF
jar cfm kotlin-scripting-compiler-impl-embeddable.jar manifest.mf -C classes .
test -s kotlin-scripting-compiler-impl-embeddable.jar
jar tf kotlin-scripting-compiler-impl-embeddable.jar > jar.list
grep -F -qx 'org/jetbrains/kotlin/scripting/configuration/ScriptingConfigurationKeys.class' jar.list
grep -F -qx 'org/jetbrains/kotlin/scripting/IdentifiersKt.class' jar.list
grep '\.class$' jar.list > classfiles.list
test "$(wc -l < classfiles.list)" -eq 76
while IFS= read -r c; do
	case "$c" in
	org/jetbrains/kotlin/scripting/*)
		;;
	*)
		echo "unexpected class $c"
		exit 1
		;;
	esac
done < classfiles.list
cat > forbidden.list << 'EOF'
org/jetbrains/kotlin/resolve/BindingContext.class
com/intellij/openapi/vfs/LocalFileSystem.class
org/jetbrains/kotlin/fir/scopes/FirScope.class
org/jetbrains/kotlin/fir/scopes/DelicateScopeAPI.class
org/jetbrains/kotlin/extensions/ExtensionPointDescriptor.class
org/jetbrains/kotlin/extensions/ProjectExtensionDescriptor.class
org/jetbrains/kotlin/compiler/plugin/CompilerPluginRegistrar.class
org/jetbrains/kotlin/resolve/extensions/ExtraImportsProviderExtension.class
org/jetbrains/kotlin/cli/FrontendConfigurationKeys.class
org/jetbrains/kotlin/K1Deprecation.class
org/jetbrains/kotlin/fir/resolve/substitution/SubstitutorByMap24Kt.class
EOF
while IFS= read -r bad; do
	if grep -F -qx "$bad" jar.list; then
		echo "forbidden $bad"
		exit 1
	fi
done < forbidden.list
desc=$(jar --describe-module --file kotlin-scripting-compiler-impl-embeddable.jar)
printf '%s\n' "$desc" | grep -F -qx 'kotlin.scripting.compiler.impl automatic'
if printf '%s\n' "$desc" | grep -F -q 'Unable'; then
	echo "describe failed"
	exit 1
fi
cat > kotlin-scripting-compiler-impl-embeddable.pom << END
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.jetbrains.kotlin</groupId>
  <artifactId>kotlin-scripting-compiler-impl-embeddable</artifactId>
  <version>%{version}</version>
  <name>kotlin-scripting-compiler-impl-embeddable</name>
  <description>Kotlin scripting compiler implementation</description>
  <url>https://github.com/JetBrains/kotlin</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.jetbrains.kotlin</groupId>
      <artifactId>kotlin-stdlib</artifactId>
      <version>%{version}</version>
    </dependency>
    <dependency>
      <groupId>org.jetbrains.kotlin</groupId>
      <artifactId>kotlin-script-runtime</artifactId>
      <version>%{version}</version>
    </dependency>
    <dependency>
      <groupId>org.jetbrains.kotlin</groupId>
      <artifactId>kotlin-scripting-common</artifactId>
      <version>%{version}</version>
    </dependency>
    <dependency>
      <groupId>org.jetbrains.kotlin</groupId>
      <artifactId>kotlin-scripting-jvm</artifactId>
      <version>%{version}</version>
    </dependency>
    <dependency>
      <groupId>org.jetbrains.kotlin</groupId>
      <artifactId>kotlin-reflect</artifactId>
      <version>%{version}</version>
    </dependency>
  </dependencies>
</project>
END

%install
set -eo pipefail
sysjar install --buildroot %{buildroot} \
	--artifact kotlin-scripting-compiler-impl-embeddable.pom:kotlin-scripting-compiler-impl-embeddable.jar \
	--file-name kotlin-scripting-compiler-impl-embeddable \
	--filelist .mfiles
idx="%{buildroot}/usr/share/sysjar/index/org.jetbrains.kotlin/kotlin-scripting-compiler-impl-embeddable.sysjar"
test -s "$idx"
grep -F -q '"version": "%{version}"' "$idx"
grep -F -q '"artifactId": "kotlin-scripting-compiler-impl-embeddable"' "$idx"
grep -F -q '/usr/share/java/kotlin-scripting-compiler-impl-embeddable.jar' "$idx"
test -s %{buildroot}%{_javadir}/kotlin-scripting-compiler-impl-embeddable.jar

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-21-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
JAR=%{buildroot}%{_javadir}/kotlin-scripting-compiler-impl-embeddable.jar
STDLIB=%{_javadir}/kotlin-stdlib-%{version}.jar
RUNTIME=%{_javadir}/kotlin-script-runtime-%{version}.jar
COMMON=%{_javadir}/kotlin-scripting-common.jar
SJVM=%{_javadir}/kotlin-scripting-jvm.jar
REFLECT=%{_javadir}/kotlin-reflect-%{version}.jar
COMPILER=/usr/share/kotlin/lib/kotlin-compiler.jar
test -s "$JAR"
test -s "$STDLIB"
test -s "$RUNTIME"
test -s "$COMMON"
test -s "$SJVM"
test -s "$REFLECT"
test -s "$COMPILER"
mkdir -p check/out
cat > check/Probe.kt << 'EOF'
import org.jetbrains.kotlin.scripting.configuration.ScriptingConfigurationKeys
import org.jetbrains.kotlin.scripting.KOTLIN_SCRIPTING_PLUGIN_ID

fun main() {
    val key = ScriptingConfigurationKeys.SCRIPT_DEFINITIONS
    val id = KOTLIN_SCRIPTING_PLUGIN_ID
    val src = ScriptingConfigurationKeys::class.java.protectionDomain.codeSource.location.path
    if (!src.endsWith("kotlin-scripting-compiler-impl-embeddable.jar")) error("src " + src)
    if (key.toString() != "SCRIPT_DEFINITIONS") error("key " + key)
    if (id != "kotlin.scripting") error("id " + id)
    println("scripting_compiler_impl_ok " + key.toString() + " " + id)
}
EOF
kotlinc -J-Xmx1g -jvm-target 1.8 -language-version 2.0 -no-stdlib -jdk-home "$JAVA_HOME" \
	-cp "$JAR:$STDLIB:$RUNTIME:$COMMON:$SJVM:$REFLECT:$COMPILER" -d check/out check/Probe.kt < /dev/null
java -cp "check/out:$JAR:$STDLIB:$RUNTIME:$COMMON:$SJVM:$REFLECT:$COMPILER" ProbeKt > check/out.txt
cat check/out.txt
grep -F -qx 'scripting_compiler_impl_ok SCRIPT_DEFINITIONS kotlin.scripting' check/out.txt

%files -f .mfiles
%license license/LICENSE.txt
%doc license/NOTICE.txt
